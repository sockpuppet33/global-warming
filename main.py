from flask import Flask

app = Flask(__name__)

# TODO app code...

@app.route("/")
def root():
  return "(|| w ||)"

app.run(debug=True)
