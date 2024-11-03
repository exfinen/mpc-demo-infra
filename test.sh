#/bin/bash

for k in RBQ-vY0TlIcSwRQ7NEp7mw yb2Fyih9oeQhhrZZ9VO1_Q CKGf569D4iWKAM_xVzc22A sae5tPzWMvJdKs9R0bbeMg wOd0CR7IJXR32lvMHCeoJA xSv2ea7pS6agQuO7RwPu3Q; do
  poetry run client-share-data $k &
done

