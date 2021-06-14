FROM continuumio/miniconda3
WORKDIR /app
VOLUME ["/cache"]
COPY . .
RUN conda create --name partybal --file conda-linux-64.lock
ENV OUTPUT="/output" BUCKET_URL="gs://partybal/"
CMD "./entrypoint.sh invoke --cache /cache --output $OUTPUT"
