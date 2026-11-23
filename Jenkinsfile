pipeline {
    agent any

    environment {
        SCANNER_HOME = tool 'SonarScanner'
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
                    coverage run -m unittest discover -s tests -v
                    coverage xml -o coverage.xml
                '''
            }
        }

        stage('Sonar Analysis') {
            steps {
                withSonarQubeEnv('SonarCloud') {
                    sh '''
                        ${SCANNER_HOME}/bin/sonar-scanner \
                          -Dsonar.organization=arpitjindal01 \
                          -Dsonar.projectKey=arpitjindal01_Jenkins-release \
                          -Dsonar.sources=. \
                          -Dsonar.tests=tests \
                          -Dsonar.exclusions=venv/**,tests/** \
                          -Dsonar.python.coverage.reportPaths=coverage.xml \
                          -Dsonar.qualitygate.wait=true
                    '''
                }
            }
        }
    }
}