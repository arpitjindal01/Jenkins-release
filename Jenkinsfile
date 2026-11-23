pipeline {
    agent any

    environment {
            ARTIFACTORY_URL = 'https://trialu143d4.jfrog.io/artifactory'
            REPO            = 'batch-runtime-local'
        }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Install and Test') {
            steps {
                sh '''
                    rm -rf venv
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    pip install coverage
                    coverage run --include=predict.py -m unittest discover -s tests -v
                    coverage xml -o coverage.xml
                '''
            }
        }
        stage('Sonar Analysis') {
            steps {
                script {
                    def scannerHome = tool name: 'SonarScanner',
                                           type: 'hudson.plugins.sonar.SonarRunnerInstallation'
                    withSonarQubeEnv('SonarCloud') {
                        sh "${scannerHome}/bin/sonar-scanner -Dsonar.qualitygate.wait=true"
                    }
                }
            }
        }
        stage('Package Metadata') {
            when { branch 'main' }
            steps {
                sh '''
                    test -f models/batch-runtime-v1.tar.gz || { echo "ERROR: model file missing"; exit 1; }
                    SHA=$(sha256sum models/batch-runtime-v1.tar.gz | cut -d' ' -f1)
                    [ -n "$SHA" ] || { echo "ERROR: could not compute SHA-256"; exit 1; }
                    VERSION="1.0.${BUILD_NUMBER}-$(echo "$GIT_COMMIT" | cut -c1-7)"
                    export VERSION SHA
                    python3 -c 'import json,os; print(json.dumps({"version":os.environ["VERSION"],"sha256":os.environ["SHA"],"commit":os.environ["GIT_COMMIT"],"build_url":os.environ["BUILD_URL"]}, indent=2))' > release.json
                    cat release.json
                '''
                archiveArtifacts artifacts: 'models/batch-runtime-v1.tar.gz, release.json', fingerprint: true
            }
        }
        stage('Artifactory Check') {
        when { branch 'main' }
        steps {
                withCredentials([string(credentialsId: 'artifactory-token', variable: 'ART_TOKEN')]) {
                    sh '''
                        echo "--- ping (no auth) ---"
                        curl -fsS "$ARTIFACTORY_URL/api/system/ping"
                        echo

                        echo "--- authenticated read of repo ---"
                        curl -fsS -H "Authorization: Bearer $ART_TOKEN" "$ARTIFACTORY_URL/api/storage/$REPO"
                        echo
                        
                    '''
                }
            }
        
            }
        stage('Publish Model') {
        when { branch 'main' }
        steps {
            withCredentials([string(credentialsId: 'artifactory-token', variable: 'ART_TOKEN')]) {
                sh '''
                    VERSION=$(python3 -c 'import json; print(json.load(open("release.json"))["version"])')
                    SHA=$(python3 -c 'import json; print(json.load(open("release.json"))["sha256"])')
                    [ -n "$VERSION" ] && [ -n "$SHA" ] || { echo "ERROR: release.json incomplete"; exit 1; }
                    URL="$ARTIFACTORY_URL/$REPO/batch-runtime/$VERSION/batch-runtime-v1.tar.gz"

                    CODE=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $ART_TOKEN" "$URL")
                    [ "$CODE" = "404" ] || { echo "ERROR: already published or check failed (HTTP $CODE)"; exit 1; }

                    curl -fsS -H "Authorization: Bearer $ART_TOKEN" -H "X-Checksum-Sha256: $SHA" \
                        -T models/batch-runtime-v1.tar.gz "$URL"

                    curl -fsS -H "Authorization: Bearer $ART_TOKEN" -o downloaded.tar.gz "$URL"
                    GOT=$(sha256sum downloaded.tar.gz | cut -d' ' -f1)
                    [ "$GOT" = "$SHA" ] || { echo "ERROR: digest mismatch ($GOT vs $SHA)"; exit 1; }

                    echo "Published $URL sha256=$SHA"
                '''
            }
        }
    }
}
}
