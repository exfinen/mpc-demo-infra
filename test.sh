#/bin/bash

for k in _Cu1YqC4f7HynDdJ6nHFEA _Cxq4gfbSs9s8s05QBBX_A o-PipYAC349zapLlzBWG7g UYvULAaqGMj7II-Tc6LgQg RBQ-vY0TlIcSwRQ7NEp7mw yb2Fyih9oeQhhrZZ9VO1_Q CKGf569D4iWKAM_xVzc22A sae5tPzWMvJdKs9R0bbeMg wOd0CR7IJXR32lvMHCeoJA; do
  poetry run client-share-data $k &
done

