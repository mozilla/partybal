FROM continuumio/miniconda3
WORKDIR /app
COPY conda-linux-64.lock .
RUN conda create --name partybal --file conda-linux-64.lock
COPY . .
ENV OUTPUT="/output" BUCKET_URL="gs://protosaur-stage-iap-static-website/partybal/"
CMD /app/entrypoint.sh invoke --updated-seconds-ago 90000 --output $OUTPUT
