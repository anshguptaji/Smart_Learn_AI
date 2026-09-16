from flask_mysqldb import MySQL

def init_db(app):
    # ---------- Database Config ----------
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = 'ansh@26Ji'
    app.config['MYSQL_DB'] = 'ai_learning'
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

    mysql = MySQL(app)

    with app.app_context():
        cur = mysql.connection.cursor()

        # ---------- Users Table ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                student_class VARCHAR(20),
                subject VARCHAR(50)
            )
        """)

        # ---------- Topics Table ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                subject VARCHAR(100),
                topic_name VARCHAR(100)
            )
        """)

        # ---------- MCQs Table ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mcqs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                topic_id INT,
                question TEXT,
                option_a VARCHAR(255),
                option_b VARCHAR(255),
                option_c VARCHAR(255),
                option_d VARCHAR(255),
                correct_option CHAR(1),
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
            )
        """)

        # ---------- Progress Table ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_email VARCHAR(100),
                topic_id INT,
                score INT DEFAULT 0,
                weak_topic BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
                FOREIGN KEY (student_email) REFERENCES users(email) ON DELETE CASCADE
            )
        """)

        mysql.connection.commit()
        cur.close()

    return mysql