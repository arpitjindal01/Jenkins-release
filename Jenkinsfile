pipeline {
    agent any

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
    }
}