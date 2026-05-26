from werkzeug.security import generate_password_hash
print(generate_password_hash('Admin123'))

# Admin query SQL
# INSERT INTO utenti (username, password, ruolo, immagine) 
# VALUES ('admin', 'scrypt:32768:8:1$0oVKoZs7bBcSgG5M$2897a280b536c0f8c15a72e5ee79849eda7fce2e823826370dce0a5206bc0d8c8e217663f64173884336d3cd4ff0c3e28b81821955fd20355db5e2642880ba2d', 'admin', 'admin_default.png');