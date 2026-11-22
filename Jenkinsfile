pipeline{
    agent any

    stages{
        stage('Install and Test'){
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                    python3 -m unittest discover -s tests -v
                '''
            }
        }

}
}
