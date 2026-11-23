pipeline{
    agent any

    stages{
        stage('Install and Test'){
            steps {
                sh '''
                    rm -rf venv
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    python3 -m unittest discover -s tests -v
                '''
            }
        }
        stage('Sonar Analysis') {
            steps {
                script {
                    sh '''sonar-scanner \
                        -Dsonar.organization=arpitjindal01 \
                        -Dsonar.projectKey=arpitjindal01_Jenkins-release'''
                    }
                }
            }

}
}
