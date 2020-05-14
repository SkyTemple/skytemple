pipeline {
    agent any
    options {
        disableConcurrentBuilds()
    }

    stages {

        stage('Build') {
            steps {
                // Setup virtual env
                sh "rm -rf .venv || true"
                sh "virtualenv .venv"

                // Run build
                sh "rm -rf dist build || true"
                sh '''. .venv/bin/activate
                      pip3 install -r requirements.txt
                      python3 setup.py bdist_wheel
                '''
            }
            post {
                always {
                    archiveArtifacts allowEmptyArchive: true, artifacts: 'dist/*whl', fingerprint: true
                }
            }
        }

        stage('Deploy to PyPI') {
            when {
                branch "release"
            }
            environment {
                TWINE    = credentials('parakoopa-twine-username-password')
            }
            steps {
                sh 'twine upload -u "$TWINE_USR" -p "$TWINE_PSW" dist/*'
            }
        }

    }

}
