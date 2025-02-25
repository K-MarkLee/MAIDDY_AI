# AI BUILD

1. Clone the project repository:  
    ```
    https://github.com/K-MarkLee/MAIDDY_AI/
    ```

2. Navigate to the projec directory:
    ```
    cd MAIDDY_AI
    ```
    
3. **Create `.env` file:**
    Create a file named `.env` in the project root directory and add the following content:
    ```
    OPENAI_API_KEY, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DATABASE_URL, SQLALCHEMY_TRACK_MODIFICATIONS, TIMEZONE
    ```

4. **Run the docker:**
    ```
    docker-compose up --build
    ```


5. Apply database migration
    ```
    docker-compose exec maiddy_ai flask db init
    docker exec -it maiddy_ai bash
    ```
    need to go inside docker file
    ```
    docker exec -it maiddy_ai bash
    ```
    need to add EXCLUDED_TABLES_AND_INDEXCES
    ```
    cd migrations
    apt-get update
    apt-get install vim
    vi env.py
    ```

   env.py
    ```
        EXCLUDED_TABLES_AND_INDEXES = [
            'users_user',
            'todo_todo',
            'schedules_schedule',
            'diaries_diary',
            'django_session',
            'token_blacklist_outstandingtoken',
            'token_blacklist_blacklistedtoken',
            'users_user_groups',
            'django_content_type',
            'auth_group_permissions',
            'django_migrations',
            'auth_group',
            'django_admin_log',
            'users_user_user_permissions',
            'auth_permission',
            # 필요한 경우 여기에 추가
        ]
        if type_ == "table" and name in EXCLUDED_TABLES_AND_INDEXES:
            return False  # 해당 테이블은 제외
        elif type_ == "index" and name in EXCLUDED_TABLES_AND_INDEXES:
            return False  # 해당 인덱스는 제외
        return True

    ...
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            include_object=include_object,
            **conf_args
        )
    
    ```
    run migration
    ```
    exit
    docker-compose exec maiddy_ai flask db stamp head
    docker-compose exec maiddy_ai flask db migrate
    ```
    edit file
    ```
    docker exec -it maiddy_ai bash
    cd migrations/versions
    vi {migration file}
    ```
    version.py
    need to add import and change embedding line
    ```
    from pgvector.sqlalchemy import Vector

    ...
    # replace embedding line into
    sa.Column('embedding', Vector(1536), nullable=True),
    
    ```
    finish migration
    ```
    exit
    docker-compose exec maiddy_ai flask db upgrade
    ```

---


<div align=center><h1>📚 STACKS</h1></div>

<div align=center> 
  <!-- Frontend -->
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white"> 
  <img src="https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white">
  <br>
  
  <!-- Backend -->
  <img src="https://img.shields.io/badge/Django%20DRF-092E20?style=for-the-badge&logo=django&logoColor=white"> 
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white">
  <img src="https://img.shields.io/badge/Postman-FF6C37?style=for-the-badge&logo=postman&logoColor=white">
  <br>
  
  <!-- AI -->
  <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white"> 
  <img src="https://img.shields.io/badge/FAISS-0086FF?style=for-the-badge&logo=faiss&logoColor=white">
  <img src="https://img.shields.io/badge/Embeddings-3A86FF?style=for-the-badge&logo=ai&logoColor=white">
  <br>
  
  <!-- Database -->
  <img src="https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white"> 
  <br>
  
  <!-- Cloud/Infrastructure -->
  <img src="https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white"> 
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white">
  <img src="https://img.shields.io/badge/Python%203.9-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <br>
  
  <!-- Collaboration -->
  <img src="https://img.shields.io/badge/JIRA-0052CC?style=for-the-badge&logo=jira&logoColor=white"> 
  <img src="https://img.shields.io/badge/Figma-F24E1E?style=for-the-badge&logo=figma&logoColor=white">
  <img src="https://img.shields.io/badge/Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white">
  <img src="https://img.shields.io/badge/Notion-000000?style=for-the-badge&logo=notion&logoColor=white">
</div>
