#/bin/bash

for k in iiTLLKD3F0URpcGCwoAhkg FQ_H-eji76N-Eq53cNfBNA u9pLKVjqMI1W6RU_Xc-OEg; do
  poetry run client-share-data $k &
done

