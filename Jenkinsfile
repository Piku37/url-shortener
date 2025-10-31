pipeline {
    agent any

    environment {
        DOCKER_IMAGE = 'url-shortener'
        DOCKER_TAG   = "${BUILD_NUMBER}"
        SONAR_PROJECT_KEY = 'url-shortener'
    }

    stages {
        stage('1. Git Checkout') {
            steps {
                echo '========== Checking out code from Git =========='
                checkout scm
                echo 'Code checkout completed successfully!'
            }
        }

        stage('2. Setup Environment') {
            steps {
                echo '========== Checking Python & Pip versions =========='
                script {
                    if (isUnix()) {
                        sh '''
                            python3 --version || python --version
                            pip3 --version || pip --version
                        '''
                    } else {
                        bat '''
                            python --version
                            pip --version
                        '''
                    }
                }
                echo 'Environment check completed!'
            }
        }

        stage('3. Install Dependencies') {
            steps {
                echo '========== Installing dependencies =========='
                script {
                    if (isUnix()) {
                        sh 'pip3 install -r requirements.txt || pip install -r requirements.txt'
                    } else {
                        bat 'pip install -r requirements.txt'
                    }
                }
            }
        }

        stage('4. Run Unit Tests') {
            steps {
                echo '========== Running unit tests =========='
                script {
                    if (isUnix()) {
                        sh 'pytest tests/ -v --junitxml=test-results.xml'
                    } else {
                        bat 'pytest tests/ -v --junitxml=test-results.xml'
                    }
                }
            }
            post {
                always {
                    junit 'test-results.xml'
                }
            }
        }

        stage('5. Code Quality (pylint/flake8)') {
            steps {
                echo '========== Linting (non-blocking) =========='
                script {
                    if (isUnix()) {
                        sh '''
                            pylint app.py || true
                            flake8 app.py --max-line-length=100 || true
                        '''
                    } else {
                        bat '''
                            pylint app.py || ver > NUL
                            flake8 app.py --max-line-length=100 || ver > NUL
                        '''
                    }
                }
            }
        }

        stage('6. SonarQube (optional)') {
            when { expression { return false } } // flip to true after SonarQube is configured
            steps {
                echo '========== SonarQube analysis =========='
                withSonarQubeEnv('SonarQube') {
                    script {
                        if (isUnix()) {
                            sh '''
                                sonar-scanner ^
                                  -Dsonar.projectKey=${SONAR_PROJECT_KEY} ^
                                  -Dsonar.sources=. ^
                                  -Dsonar.python.coverage.reportPaths=coverage.xml
                            '''
                        } else {
                            bat '''
                                sonar-scanner ^
                                  -Dsonar.projectKey=%SONAR_PROJECT_KEY% ^
                                  -Dsonar.sources=. ^
                                  -Dsonar.python.coverage.reportPaths=coverage.xml
                            '''
                        }
                    }
                }
            }
        }

        stage('7. Build Docker Image') {
            steps {
                echo '========== Building Docker image =========='
                script {
                    if (isUnix()) {
                        sh """
                            docker version
                            docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .
                            docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest
                        """
                    } else {
                        bat """
                            docker version
                            docker build -t %DOCKER_IMAGE%:%DOCKER_TAG% .
                            docker tag %DOCKER_IMAGE%:%DOCKER_TAG% %DOCKER_IMAGE%:latest
                        """
                    }
                }
            }
        }

        stage('8. Deploy (local Docker)') {
            steps {
                echo '========== Deploying container =========='
                script {
                    if (isUnix()) {
                        sh """
                            docker stop url-shortener || true
                            docker rm url-shortener || true
                            docker run -d --name url-shortener -p 5000:5000 ${DOCKER_IMAGE}:latest
                            sleep 5
                            curl -f http://localhost:5000/health
                        """
                    } else {
                        bat """
                            docker stop url-shortener 2>NUL || ver > NUL
                            docker rm url-shortener 2>NUL || ver > NUL
                            docker run -d --name url-shortener -p 5000:5000 %DOCKER_IMAGE%:latest
                            powershell -Command "Start-Sleep -s 5"
                            powershell -Command "Invoke-WebRequest -UseBasicParsing http://localhost:5000/health | Out-Null"
                        """
                    }
                }
                echo 'Application deployed!'
            }
        }
    }

    post {
        success {
            echo '========================================='
            echo '✅ Pipeline completed successfully!'
            echo '========================================='
            echo 'App URL: http://localhost:5000'
            echo '========================================='
        }
        failure {
            echo '========================================='
            echo '❌ Pipeline failed!'
            echo '========================================='
        }
        always {
            echo 'Cleaning workspace artifacts (kept by Jenkins automatically).'
        }
    }
}
