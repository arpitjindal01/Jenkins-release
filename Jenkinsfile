pipeline{
    agent {label 'any'}

    stages{
        stage('Install and Test'){
            steps{
                script {
                    sh 'pip install -r requirements.txt'
                    sh 'python3 -m unittest discover -s tests -v'
                }
                }
        }

}
}
