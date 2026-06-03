from flask import Flask, request
from twilio.rest import Client
from dotenv import load_dotenv
import os, json
from datetime import datetime

load_dotenv()
app = Flask(__name__)
@app.route("/envoyer")
def envoyer():
    nom = request.args.get("nom", "client")
    numero = request.args.get("numero")
    ticket = request.args.get("ticket", "0000")
    if not numero:
     return "Numéro manquant!", 400
    envoyer_sms(numero, nom, ticket)
    return "Serveur SMS actif!", 200

@app.route("/test")
def test():
    envoyer_sms(MON_NUMERO, "Alioune", "1001")
    return "SMS envoyé!", 200
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
MON_NUMERO = os.getenv("MON_NUMERO")


def envoyer_sms(numero, nom, ticket_id):
    print(f"SID: {ACCOUNT_SID[:5] if ACCOUNT_SID else 'NONE'}")
    print(f"TOKEN: {AUTH_TOKEN[:5] if AUTH_TOKEN else 'NONE'}")
    print(f"NUMERO: {numero}")
    client= Client(ACCOUNT_SID, AUTH_TOKEN)
    msg = f"Envoyer par Galsen\nBonjour {nom}, demande #{ticket_id} resolue.\nComment avez vous trouvez le service ? 1=Mauvais 2=Correct 3=Excellent"
    client.messages.create(body=msg, from_=TWILIO_NUMBER, to=numero)
    print(f"SMS envoye a {numero}")

def sauvegarder(numero, score):
    f = "resultats.json"
    data = json.load(open(f)) if os.path.exists(f) else []
    data.append({"numero": numero, "score": score, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
    json.dump(data, open(f, "w"), indent=4)

@app.route("/reponse", methods=["POST"])
def reponse():
    numero = request.form.get("From")
    scores = {"1": "Mauvais", "2": "Correct", "3": "Excellent"}
    score = scores.get(request.form.get("Body").strip(), "Inconnu")
    sauvegarder(numero, score)
    return "", 200

if __name__ == "__main__":
     app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
     
@app.route("/debug")
def debug():
    return {
        "ACCOUNT_SID": "OK" if ACCOUNT_SID else "MANQUANT",
        "AUTH_TOKEN": "OK" if AUTH_TOKEN else "MANQUANT",
        "TWILIO_PHONE_NUMBER": "OK" if TWILIO_NUMBER else "MANQUANT",
        "MON_NUMERO": "OK" if MON_NUMERO else "MANQUANT"
    }

@app.route("/stats")
def stats():
    fichier = "resultats.json"
    if not os.path.exists(fichier):
        return "Aucune réponse encore.", 200

    data = json.load(open(fichier))
    total = len(data)
    mauvais = sum(1 for r in data if r["score"] == "Mauvais")
    correct = sum(1 for r in data if r["score"] == "Correct")
    excellent = sum(1 for r in data if r["score"] == "Excellent")

    html = f"""
    <h1>📊 Statistiques de Satisfaction</h1>
    <p>Total de réponses : <b>{total}</b></p>
    <p>😞 Mauvais : <b>{mauvais}</b> ({round(mauvais/total*100) if total else 0}%)</p>
    <p>😐 Correct : <b>{correct}</b> ({round(correct/total*100) if total else 0}%)</p>
    <p>😊 Excellent : <b>{excellent}</b> ({round(excellent/total*100) if total else 0}%)</p>
    """
    return html, 200
