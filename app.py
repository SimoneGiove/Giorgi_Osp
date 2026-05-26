from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid

app = Flask(__name__)
app.secret_key = "chiave_super_segreta"

def db():
    connessione = pymysql.connect(
        host="192.168.51.245",
        user="simgiove07",
        database="simgiove07",
        cursorclass=pymysql.cursors.DictCursor
    )
    return connessione

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nome = request.form['nome']
        ruolo = request.form['ruolo']
        file = request.files.get('immagine')

        IMG = "static/img"
        img = 'default.png'
        if file and file.filename != "":
            img = secure_filename(file.filename)

        hashed_pw = generate_password_hash(password)
        conn = db()

        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM utenti WHERE username = %s", (username))
                if cursor.fetchone():
                    flash("Username già esistente!")
                    return redirect(url_for('register'))
                
                cursor.execute("INSERT INTO utenti(username, password, ruolo, immagine) VALUES (%s, %s, %s, %s)", (username, hashed_pw, ruolo, img))
                id_utente = cursor.lastrowid

                if ruolo == "dottore":
                    codice_dottore = request.form['codice_dottore']
                    specializzazione = request.form['specializzazione']
                    cursor.execute("INSERT INTO dottori(codice_dottore, nome, specializzazione, id_utente) VALUES (%s, %s, %s, %s)", (codice_dottore, nome, specializzazione, id_utente))
                    conn.commit()
                    flash("Registrazione completata!")
                    return redirect(url_for('login'))
                elif ruolo == "paziente":
                    cf = request.form['cf']
                    data_nascita = request.form['data_nascita']
                    cursor.execute("INSERT INTO pazienti(codice_fiscale, nome, data_nascita, id_utente) VALUES (%s, %s, %s, %s)", (cf, nome, data_nascita, id_utente))
                    conn.commit()
                    flash("Registrazione completata!")
                    return redirect(url_for('login'))
                else:
                    flash("Ruolo non valido!")
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']
        conn = db()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM utenti WHERE username = %s", (username,))
                utente = cursor.fetchone()

                if not utente:
                    flash("Utente non trovato")
                    return redirect(url_for('login'))

                if not check_password_hash(utente['password'], password_candidate):
                    flash("Password errata")
                    return redirect(url_for('login'))

                img = utente.get('immagine')
                if not img or img == "None":
                    img = 'default.png'

                session['username'] = utente['username']
                session['ruolo'] = utente['ruolo']
                session['immagine'] = img

                if utente['ruolo'] == 'dottore':
                    cursor.execute("SELECT * FROM dottori WHERE id_utente = %s", (utente['id'],))
                    dottore = cursor.fetchone()
                    if dottore:
                        session['nome'] = dottore['nome']
                        session['codice_dottore'] = dottore['codice_dottore']
                        session['specializzazione'] = dottore['specializzazione']
                elif utente['ruolo'] == 'paziente':
                    cursor.execute("SELECT * FROM pazienti WHERE id_utente = %s", (utente['id'],))
                    paziente = cursor.fetchone()
                    if paziente:
                        session['nome'] = paziente['nome']
                        session['cf'] = paziente['codice_fiscale']
                        session['data_nascita'] = str(paziente['data_nascita'])
                else:
                    session['nome'] = 'Amministratore'
                flash("Bentornato!")
                return redirect(url_for('dashboard'))
        finally:    
            conn.close()
    return render_template('login.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session: 
        flash("Per utilizzare la dashboard sei pregato di loggarti.")
        return redirect(url_for('login'))

    cards = []
    dottori = []
    pazienti = []

    conn = db()
    try:
        with conn.cursor() as cursor:
            if session.get('ruolo') == 'admin':
                cursor.execute("SELECT codice_dottore, nome FROM dottori")
                dottori = cursor.fetchall()
                cursor.execute("SELECT codice_fiscale, nome FROM pazienti")
                pazienti = cursor.fetchall()
    finally:
        conn.close()
    img = session.get('immagine')
    if not img or img == "None":
        img = 'default.png'
    return render_template('dashboard.html', username=session['username'], cards=cards, nome=session.get('nome', 'Amministratore'), ruolo=session.get('ruolo'), immagine=img, dottori=dottori, pazienti=pazienti)

@app.route('/crea_appuntamento', methods=['POST'])
def crea_appuntamento():
    if 'username' not in session or session.get('ruolo') == 'paziente':
        flash("Accesso negato. Solo gli amministratori possono creare appuntamenti.")
        return redirect(url_for('login'))

    cod_doc = request.form.get('codDoc')
    cf_paz = request.form.get('cfPaz')
    data_app = request.form.get('data_appuntamento')
    ora_app = request.form.get('ora')

    if not cod_doc or not cf_paz or not data_app or not ora_app:
        flash("Tutti i campi sono obbligatori!")
        return redirect(url_for('dashboard'))

    conn = db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO appuntamenti (codDoc, cfPaz, data_appuntamento, ora) VALUES (%s, %s, %s, %s)", (cod_doc, cf_paz, data_app, ora_app))
            conn.commit()
            flash("Appuntamento creato con successo!")
    finally:
        conn.close()
    return redirect(url_for('dashboard'))


@app.route("/dottori")
def dottori():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = db()
    try:
        with conn.cursor() as cursor:
            if session.get('ruolo') == 'paziente':
                cursor.execute("SELECT DISTINCT d.* FROM dottori AS d JOIN appuntamenti AS a ON d.codice_dottore = a.codDoc WHERE a.cfPaz = %s", (session.get('cf'),))
            else:
                cursor.execute("SELECT * FROM dottori")
            dottori = cursor.fetchall()
    finally:
        conn.close()
    return render_template("dottori.html", dottori=dottori)


@app.route("/pazienti")
def pazienti():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = db()
    try:
        with conn.cursor() as cursor:
            if session.get('ruolo') == 'dottore':
                cursor.execute("SELECT DISTINCT p.* FROM pazienti AS p JOIN appuntamenti AS a ON p.codice_fiscale = a.cfPaz WHERE a.codDoc = %s", (session.get('codice_dottore'),))
            else:
                cursor.execute("SELECT * FROM pazienti")
            pazienti = cursor.fetchall()
    finally:
        conn.close()
    return render_template("pazienti.html", pazienti=pazienti)


@app.route("/visite/<codice>")
def visite(codice):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = db()
    try:
        with conn.cursor() as cur:
            if codice == "none":
                cur.execute("SELECT a.* FROM appuntamenti AS a JOIN dottori AS d ON a.codDoc = d.codice_dottore JOIN pazienti AS p ON a.cfPaz = p.codice_fiscale")
            else:
                cur.execute("SELECT a.* FROM appuntamenti AS a JOIN dottori AS d ON a.codDoc = d.codice_dottore JOIN pazienti AS p ON a.cfPaz = p.codice_fiscale WHERE a.codDoc = %s OR a.cfPaz = %s", (codice, codice))
            visite = cur.fetchall()
    finally:
        conn.close()
    return render_template("visite.html", visite=visite, codice=codice)

@app.route('/logout')
def logout():
    session.clear()
    flash("Sloggato con successo!")
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)