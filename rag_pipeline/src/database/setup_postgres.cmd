@echo off
echo ===== SETUP POSTGRESQL FOR CHATBOT =====

echo 1. Stop old container...
docker stop postgres_chatbot 2>nul
docker rm postgres_chatbot 2>nul

echo 2. Start PostgreSQL container (Port 5433)...
docker run -d --name postgres_chatbot -e POSTGRES_PASSWORD=123456 -p 5433:5432 postgres:15

echo 3. Wait for startup...
timeout /t 15 /nobreak >nul

echo 4. Create database...
docker exec postgres_chatbot psql -U postgres -c "CREATE DATABASE chatbot_db;" 2>nul

echo 5. Create table...
docker cp rag_pipeline\src\database\create_table.sql postgres_chatbot:/tmp/
docker exec postgres_chatbot psql -U postgres -d chatbot_db -f /tmp/create_table.sql

echo ===== DONE =====
echo Connection: localhost:5433
echo Database: chatbot_db  
echo User: postgres
echo Password: 123456
pause 