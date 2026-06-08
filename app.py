from flask import Flask, request
from twilio.rest import Client
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os, json
from datetime import datetime

load_dotenv()
app = Flask(__name__)

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
MON_NUMERO = os.getenv("MON_NUMERO")


def envoyer_sms(numero, nom, ticket_id):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    msg = f"Envoyer par Galsen\nBonjour {nom}, demande #{ticket_id} resolue.\nComment avez vous trouvez le service ? 1=Mauvais 2=Correct 3=Excellent"
    client.messages.create(body=msg, from_=TWILIO_NUMBER, to=numero)
    print(f"SMS envoye a {numero}")

def sauvegarder(numero, score):
    f = "resultats.json"
    data = json.load(open(f)) if os.path.exists(f) else []
    data.append({"numero": numero, "score": score, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
    json.dump(data, open(f, "w"), indent=4)

def envoyer_email_alerte(numero, commentaire):
    print(f"Envoi email pour commentaire: {commentaire}")
    try:
        message = Mail(
            from_email="swiftsystems@gmail.com",
            to_emails="aliounediallo704@gmail.com",
            subject="Nouveau commentaire client !",
            html_content=f"""
            <h2>Un client a laisse un commentaire</h2>
            <p><b>Numero :</b> {numero}</p>
            <p><b>Commentaire :</b> {commentaire}</p>
            """
        )
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(f"Email envoye! Status: {response.status_code}")
    except Exception as e:
        print(f"Erreur email: {e}")

@app.route("/envoyer")
def envoyer():
    nom = request.args.get("nom", "client")
    numero = request.args.get("numero")
    ticket = request.args.get("ticket", "0000")
    if not numero:
        return "Numero manquant!", 400
    envoyer_sms(numero, nom, ticket)
    return "SMS envoye!", 200

@app.route("/reponse", methods=["GET", "POST"], strict_slashes=False)
def reponse():
    numero = request.form.get("From") or request.args.get("From")
    body = request.form.get("Body") or request.args.get("Body")
    print(f"Recu: numero={numero}, body={body}")

    if not body:
        return "OK", 200
    
    body = body.strip()
    scores = {"1": "Mauvais", "2": "Correct", "3": "Excellent"}
    
    if body in scores:
        score = scores[body]
        sauvegarder(numero, score)
        
        if body == "1":
            msg = "Merci pour votre retour. Nous sommes desoles que votre experience n'ait pas ete satisfaisante. Un membre de notre equipe vous contactera prochainement."
        elif body == "2":
            msg = "Merci pour votre retour ! Nous prenons note de votre evaluation."
        elif body == "3":
            msg = "Merci pour votre excellente evaluation ! Souhaitez-vous laisser un commentaire ? Repondez directement a ce message."
        
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(body=msg, from_=TWILIO_NUMBER, to=numero)
    
    else:
        # C'est un commentaire après le 3
        envoyer_email_alerte(numero, body)
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(
            body="Merci pour votre commentaire ! Nous en prendrons compte.",
            from_=TWILIO_NUMBER,
            to=numero
        )
    
    return "", 200

@app.route("/stats")
def stats():
    fichier = "resultats.json"
    if not os.path.exists(fichier):
        return "Aucune reponse encore.", 200
    data = json.load(open(fichier))
    total = len(data)
    mauvais = sum(1 for r in data if r["score"] == "Mauvais")
    correct = sum(1 for r in data if r["score"] == "Correct")
    excellent = sum(1 for r in data if r["score"] == "Excellent")
    html = f"""
    <h1>Statistiques de Satisfaction</h1>
    <p>Total : <b>{total}</b></p>
    <p>Mauvais : <b>{mauvais}</b> ({round(mauvais/total*100) if total else 0}%)</p>
    <p>Correct : <b>{correct}</b> ({round(correct/total*100) if total else 0}%)</p>
    <p>Excellent : <b>{excellent}</b> ({round(excellent/total*100) if total else 0}%)</p>
    """
    return html, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

