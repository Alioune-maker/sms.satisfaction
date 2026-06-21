from flask import Flask, request
from twilio.rest import Client
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os, json
from datetime import datetime
from supabase import create_client
load_dotenv()
app = Flask(__name__)

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
MON_NUMERO = os.getenv("MON_NUMERO") 
en_attente_commentaire = {}
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def envoyer_sms(numero, nom, ticket_id):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    msg = f"Envoyer par swiftsystems\nBonjour {nom}, demande #{ticket_id} resolue.\nComment avez vous trouvez le service ? 1=Excellent 2=Correct 3=Mauvais"
    client.messages.create(body=msg, from_=TWILIO_NUMBER, to=numero)
    print(f"SMS envoye a {numero}")

def sauvegarder(numero, score, commentaire=None):
    supabase.table("reponses").insert({
        "numero": numero,
        "score": score,
        "commentaire": commentaire
    }).execute()
    print(f"Sauvegarde dans Supabase: {score}")

def envoyer_sms_alerte(numero_client, commentaire):
    # Sauvegarder le commentaire dans Supabase
    supabase.table("commentaires").insert({
        "numero": numero_client,
        "commentaire": commentaire
    }).execute()
    
    # Envoyer SMS d'alerte
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    msg = f"ALERTE - Nouveau commentaire client!\nNumero: {numero_client}\nCommentaire: {commentaire}"
    client.messages.create(body=msg, from_=TWILIO_NUMBER, to=MON_NUMERO)
    print(f"SMS alerte envoye!")

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
    scores = {"1": "Excellent", "2": "Correct", "3": "Mauvais"}
    
    # Vérifier si ce numéro attend un commentaire
    etat = supabase.table("etats").select("*").eq("numero", numero).execute().data
    en_attente = len(etat) > 0 and etat[0]["en_attente"]
    
    if en_attente:
        # C'est un commentaire
        supabase.table("etats").delete().eq("numero", numero).execute()
        envoyer_sms_alerte(numero, body)
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(
            body="Merci pour votre commentaire ! Nous en prendrons compte.",
            from_=TWILIO_NUMBER,
            to=numero
        )
    elif body in scores:
        score = scores[body]
        sauvegarder(numero, score)
        if body == "1":
            msg = "Merci pour votre excellente evaluation !"
        elif body == "2":
            msg = "Merci pour votre retour ! Nous prenons note de votre evaluation."
        elif body == "3":
            msg = "Merci pour votre retour. Nous sommes desoles. Souhaitez-vous laisser un commentaire ? Repondez directement a ce message."
            supabase.table("etats").upsert({"numero": numero, "en_attente": True}).execute()
    
    return "", 200

@app.route("/stats")
def stats():
    try:
        data = supabase.table("reponses").select("*").execute().data
        total = len(data)
        mauvais = sum(1 for r in data if r["score"] == "Mauvais")
        correct = sum(1 for r in data if r["score"] == "Correct")
        excellent = sum(1 for r in data if r["score"] == "Excellent")
        html = f"""
        <h1>Statistiques de Satisfaction</h1>
        <p>Total : <b>{total}</b></p>
        <p>😞 Mauvais : <b>{mauvais}</b> ({round(mauvais/total*100) if total else 0}%)</p>
        <p>😐 Correct : <b>{correct}</b> ({round(correct/total*100) if total else 0}%)</p>
        <p>😊 Excellent : <b>{excellent}</b> ({round(excellent/total*100) if total else 0}%)</p>
        """
        return html, 200
    except Exception as e:
        return f"Erreur: {e}", 500