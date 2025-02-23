web: gunicorn bot:app --bind 0.0.0.0:$PORT
worker1: gunicorn inventory:app --bind 0.0.0.0:5001
worker2: gunicorn scheduling:app --bind 0.0.0.0:5002