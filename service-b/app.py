from flask import Flask, request
import requests
import os

app = Flask(__name__)

@app.route('/api')
def api():
    return "World"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999)
