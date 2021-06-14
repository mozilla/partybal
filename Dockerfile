FROM continuumio/miniconda3
WORKDIR /app
VOLUME ["/cache"]
COPY conda-linux-64.lock .
RUN conda create --name partybal --file conda-linux-64.lock
COPY . .
ENV OUTPUT="/output" BUCKET_URL="gs://partybal/"
CMD "./entrypoint.sh invoke --cache /cache --output $OUTPUT"
