import os
import base64
import secrets
import chess

from tensorflow import keras
import tensorflow as tf

from chesscompress import learn, uci
from flask import Flask, redirect, url_for, request, make_response, session, render_template, Markup


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)

random_secret_key = secrets.token_urlsafe(32)
app.config.update(
    DEBUG=False,
    SECRET_KEY=random_secret_key
)

@app.route("/")
def index():
    fen = base64.b64decode(request.args.get('fen')).decode()
    # benchmarker = learn.Learn(tepid=0.01)

    evaluator = uci.Uci()
    # board = Board(fen=fen)
    # results = benchmarker.analyze_dataset(board)
    legal_moves, results_analysis = evaluator.analyze(fen=fen)
    return zip(*list(legal_moves), *list(results_analysis)) 
    
