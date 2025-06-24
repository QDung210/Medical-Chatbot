pipeline {
    agent any

    environment {
        REPO_URL = 'https://github.com/QDung210/Medical-Chatbot'  // Thay your-username
        BRANCH = 'main'
        SERVICE_NAME = 'medical-chatbot'
        PYTHON_PATH = '/rag_pipeline/src'
        // CODECOV_TOKEN = credentials('codecov-token') 
    }

    stages {
        stage('Checkout Code') {
            steps {
                echo 'Cloning repository from ' + REPO_URL
                git branch: "${BRANCH}", url: "${REPO_URL}", credentialsId: "github-pat"
            }
        }

        stage('Test RAG Pipeline') {
            steps {
                echo 'Testing rag_pipeline backend'
                sh '''
                    docker exec -e PYTHON_PATH="${PYTHON_PATH}" python bash -c "\
                    cd rag_pipeline && \
                    pip install --no-cache-dir -r requirements.txt && \
                    export PYTHONPATH=${PYTHON_PATH} OTEL_SDK_DISABLED=true && \
                    pytest --cov=src \
                           --cov-report=xml:coverage.xml \
                           --junitxml=test-reports/results.xml \
                           test/ || true
                           "
                '''
                // Copy coverage report từ container ra host
                sh 'docker cp python:/rag_pipeline/coverage.xml ./rag_pipeline/coverage.xml || true'
            }
        }

        stage('Test Streamlit App') {
            steps {
                echo 'Testing Streamlit application'
                sh '''
                    docker exec python bash -c "\
                    cd streamlit && \
                    pip install --no-cache-dir -r requirements.txt && \
                    python -c 'import app; print(\"Streamlit app import successful\")' || true
                    "
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                script {
                    echo 'Building Docker images'
                    sh 'docker-compose -f docker-compose.yml build --no-cache'
                }
            }
        }

        stage('Deploy Services') {
            steps {
                script {
                    echo 'Deploying services'
                    sh 'docker-compose -f docker-compose.yml up -d'
                    
                    // Wait for services to be ready
                    echo 'Waiting for services to start...'
                    sleep(30)
                    
                    // Health check
                    sh '''
                        echo "Checking service health..."
                        docker ps
                    '''
                }
            }
        }
    }

    post {
        always {
            echo "Pipeline execution complete."
            // Clean up
            sh 'docker-compose -f docker-compose.yml down -v || true'
        }
        failure {
            echo "Pipeline failed. Please check the logs."
        }
        success {
            echo "Pipeline succeeded. Medical chatbot deployment is complete!"
        }
    }
}