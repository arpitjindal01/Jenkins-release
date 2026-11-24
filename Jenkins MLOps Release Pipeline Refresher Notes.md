# Jenkins MLOps Release Pipeline: Refresher Notes

Arpit Jindal · Notes as of 24 Nov 2026

## 1. What this project is

A Jenkins release pipeline for a small scikit-learn model that predicts batch runtime (minutes) from a record count. The release artifact is `models/batch-runtime-v1.tar.gz`, containing `model.pkl`, `manifest.json` and `requirements.txt`. 10,000 records should predict about 25 minutes (slope 0.002, intercept 5).

**Setup**

- Repo: `arpitjindal01/Jenkins-release` (GitHub), Declarative Multibranch Pipeline, root `Jenkinsfile`
- Jenkins on an Ubuntu EC2 instance, `ap-south-1`, built-in node, `agent any`
- Code quality: SonarQube Cloud (free plan). Org `arpitjindal01`, project key `arpitjindal01_Jenkins-release`
- Artifact store: JFrog Artifactory trial, Generic local repo `batch-runtime-local`
- Runtime on the box: Python 3.14, scikit-learn 1.9.1 (the model was pickled with 1.6.1 on Python 3.9.6)

## 2. Pipeline as built

```
Install and Test -> Sonar Analysis -> Package Metadata -> Publish Model
  -> Promote DEV -> Deploy DEV -> Approve QA -> Promote QA
```

All stages after Sonar run on `main` only (`when { branch 'main' }`). Pipeline-level `environment` holds `ARTIFACTORY_URL` and `REPO`.

| Stage | What it does | How it was proven |
| --- | --- | --- |
| **Install and Test** | Fresh venv, `pip install -r requirements.txt`, `coverage run` of the 4 unit tests, `coverage xml` | 4 tests pass, 65% coverage on `predict.py` |
| **Sonar Analysis** | Runs the scanner with `-Dsonar.qualitygate.wait=true`. A failed gate makes the scanner exit non-zero, so the build fails | A deliberately bad commit (hardcoded password, uncovered code) gave `QUALITY GATE STATUS: FAILED` and the next stage was skipped. A revert went green |
| **Package Metadata** | Checks the model exists, computes SHA-256, builds version `1.0.<BUILD_NUMBER>-<short commit>`, writes `release.json` with Python `json.dumps`, archives model and JSON | Digest on the Mac (`shasum -a 256`) matched `release.json` |
| **Publish Model** | Reads version and SHA from `release.json`, refuses to overwrite (expects HTTP 404 at the target path), uploads with `X-Checksum-Sha256`, downloads again and compares digests | Build 30 published `batch-runtime/1.0.30-acf82f9/`, digests matched |
| **Promote DEV** | Writes `environments/dev/current.json` (pointer: env, version, sha256), validates the JSON before upload | Pointer visible in JFrog with correct keys |
| **Deploy DEV** | Reads the pointer (not `release.json`), downloads that version, compares digest to the pointer's `sha256`, unpacks | Log ended with `DEV deployed <version> sha256=...` |
| **Approve QA** | `input` step, `submitter`, `submitterParameter`, 1-hour timeout, `agent none` | Build paused, approved by `admin` |
| **Promote QA** | Reads DEV's pointer, writes the QA pointer with `approved_by`, verifies digest, unpacks to `/var/lib/jenkins/deployments/qa`, runs a prediction health check | `QA predicts: 25.0` |

PROD was deliberately skipped. It would be the same two stages reading QA's pointer with its own approver variable.

## 3. Core concepts (the interview answers)

- **Checksum (SHA-256):** a content fingerprint. Same bytes give the same string, one changed byte gives a completely different one, and it cannot be reversed. It is the artifact's identity, so every stage can prove it handles the exact bytes that passed testing. It proves unchanged, not correct or safe.
- **Releases are immutable, pointers are mutable.** One copy of the model lives at `batch-runtime/<version>/`. Environments are small JSON pointers saying which version and digest they serve. Promotion moves a pointer; it never rebuilds or copies the model.
- **Get, check, put.** Every stage fetches something, checks it matches what was promised, and puts it somewhere.
- **Producer and consumer.** Promote writes the pointer (the decision). Deploy reads the pointer and acts on it (the action). Because the consumer reads the pointer, rollback only needs to restore an old pointer.
- **Quality gate stops the release.** A failing gate fails the build before any release stage runs.
- **Jenkins fingerprint vs SHA-256:** `fingerprint: true` records an MD5 inside Jenkins to trace which build produced a file. It is Jenkins bookkeeping only. Verification uses the portable SHA-256 in `release.json`, Artifactory and the pointers.
- **Artifactory vs S3:** S3 alone could do the job (versioning, conditional writes, IAM). Artifactory adds artifact search, build info and retention, and is a common enterprise pattern.
- **Where is it deployed?** Not in Artifactory. Artifactory stores releases and pointers. Deploy places a verified copy where it runs: first a Jenkins server folder, next S3.

## 4. Reusable patterns

**Stage skeleton**

```groovy
stage('Name') {
    when { branch 'main' }
    steps {
        withCredentials([string(credentialsId: 'artifactory-token', variable: 'ART_TOKEN')]) {
            sh '''
                ...
            '''
        }
    }
}
```

**Rules for the shell block**

- Use single-quoted `'''` so Groovy never interpolates secrets. The shell reads `$ART_TOKEN` from the environment and Jenkins masks it.
- One `sh` block per stage, because shell variables do not carry between `sh` steps.
- `/bin/sh` is dash on Ubuntu, so no `${VAR:0:7}`. Use `cut -c1-7`.
- Build JSON with `python3 -c 'import json,os; print(json.dumps({...}))'`, never with `echo`. Remember to `export` variables Python reads.
- Build, validate, then upload. Checks only help if they run before the upload.

**Guard pattern**

```bash
[ condition ] || { echo "ERROR: message"; exit 1; }
```

**Artifactory calls**

```bash
curl -fsS -H "Authorization: Bearer $ART_TOKEN" -o file URL      # download
curl -fsS -H "Authorization: Bearer $ART_TOKEN" -T file URL       # upload
```

`-f` turns an HTTP error into a failed stage. Leave `-f` off only when you want to read the status code (the overwrite guard uses `-w '%{http_code}'`).

**Three variables for digest checks**

- `VERSION`: which release folder to fetch
- `WANT`: the digest the pointer promised
- `GOT`: the digest of what was actually downloaded

The guard is `GOT` equals `WANT`, never a digest recomputed from the same local file.

**Helpers:** Jenkins **Pipeline Syntax** (snippet generator) writes step syntax for you. Copy a working stage and edit it rather than writing from memory.

## 5. Problems hit and how they were fixed

| Symptom | Cause | Fix |
| --- | --- | --- |
| `null/bin/sonar-scanner: not found` | Scanner tool returned `null`: no installer added under SonarQube Scanner installations | Add installer (Maven Central), resolve with `tool name: 'SonarScanner', type: 'hudson.plugins.sonar.SonarRunnerInstallation'` |
| Re-running showed the old command | Jenkins ran the previous Jenkinsfile | Commit and push, trigger a fresh branch build |
| `Not authorized or organization not found` | Jenkins credential held a 1180-character wrong secret (a SonarCloud token is about 40) | Replace with a fresh token as Secret text. A debug stage printing token length and calling `/api/authentication/validate` found it |
| Jenkinsfile syntax error | A stage outside `stages {}` and `environment {}` inside `stages {}` | `environment` at pipeline level, all stages inside `stages` |
| Build waiting for an executor for 20 minutes | Built-in node offline: free disk 982 MiB, below the 1 GiB threshold | Deleted venvs and pip cache, then resized the volume. Add `buildDiscarder` to limit retention |
| `environments/____/current.json` created | A blank in a template was never filled in. Upload was green anyway | Fix the path, delete the stray folder. A green upload proves bytes arrived, not that they are right |
| `JSONDecodeError` in Deploy DEV | `echo` in dash stripped the quotes. The file was 105 bytes instead of about 117 | Build the pointer with Python and validate before upload |
| Upload after the fix still broken | The Python line was placed after the `curl` upload | Order matters: build, validate, upload |
| `KeyError: APPROVER` | `submitterParameter` only exists inside the stage with the `input` | Copy it into `env.QA_APPROVER` in a `script` block |
| `approved_by` was `unknown` | The declared `environment { QA_APPROVER = 'unknown' }` default overrode the runtime value | Remove the declared default, add a guard that fails if the approver is empty or `unknown` (**still to apply and verify**) |
| GitHub `403` on commit status | Token lacks commit-status permission | Open item below |

## 6. Current state of evidence

- Build 30: Package, Publish, verified digest `057f7b5d...c83`, release `1.0.30-acf82f9`
- Build 36: DEV deploy and QA promotion, QA health check returned 25.0
- Artifactory layout:
  - `batch-runtime/<version>/batch-runtime-v1.tar.gz` (immutable)
  - `environments/dev/current.json`, `environments/qa/current.json` (mutable pointers)
- Server folders: `/var/lib/jenkins/deployments/qa` (and the DEV deploy folder in the workspace)

## 7. Open items (parked)

- **Approver bug:** apply the fix in section 5 and confirm `approved_by` shows `admin`
- **Disk:** volume resized. Confirm `buildDiscarder` (keep 10 builds, 5 artifact sets) is in the Jenkinsfile
- **Cleanup:** remove the `Artifactory Check` stage if still present
- **scikit-learn mismatch:** model pickled with 1.6.1, running 1.9.1 on Python 3.14. Plan: regenerate the model under the runtime that Lambda will use
- **Hardening:** rotate any token pasted into chat, check or remove security group rule `sgr-0d0a68df578089380` on `sg-0dce77427c5ec679e`, fix the GitHub 403 (Commit statuses read and write), add a server-side no-overwrite permission in Artifactory
- **Optional failure tests:** immutability (republish the same version), 401 and 404 on Artifactory, checksum rejection, health-check red run
- **Not done:** rollback (needs saved pointer history), the 26-minute vs 25-minute demo, PROD, CodeBuild, architecture diagram, runbook
- **Simplification idea:** move inline shell into `scripts/*.sh` (for example `promote.sh dev`) so the Jenkinsfile reads as a list of steps

## 8. Next: AWS (agreed plan)

```
Artifactory (releases + pointers)
   -> Deploy stage: read pointer, fetch, verify SHA-256
   -> S3: s3://BUCKET/dev/model.pkl, s3://BUCKET/qa/model.pkl
   -> Lambda + Function URL (batch endpoint): POST {records: 10000} -> {minutes: 25.0}
```

| Step | Work | Proof |
| --- | --- | --- |
| 1 | S3 bucket in `ap-south-1` (public access blocked, versioning on), IAM policy `jenkins-batch-runtime-s3`, role `jenkins-ec2-role` attached to the instance, AWS CLI installed | `sudo -u jenkins aws sts get-caller-identity` shows the role. `aws s3 cp` and `ls` work with no keys |
| 2 | Deploy and Promote stages copy to S3 prefixes with `aws s3 cp` after the digest check | Objects appear under `dev/` and `qa/` |
| 3 | Regenerate the model under one runtime, write a Lambda that loads `s3://BUCKET/<env>/model.pkl` | Function URL returns 25.0 for 10,000 records |
| 4 | Health check calls the endpoint. Publish the 26-minute model and show QA 26 vs DEV 25 | One screenshot with both answers |

Later options: CodeBuild as a verification stage for the exact commit (Jenkins starts it, waits, fails the release if it fails), SageMaker Batch Transform as a heavier extension. Avoid a real-time SageMaker endpoint, which bills every hour.

## 9. One-line interview summary

Every commit is tested and quality-gated. On `main` it gets a version and SHA-256, is published immutably to Artifactory and verified by re-download, then promoted through environments by moving digest-carrying pointers. A separate consumer reads the pointer, verifies the digest, deploys, and runs a prediction health check. QA needs a named human approval.
