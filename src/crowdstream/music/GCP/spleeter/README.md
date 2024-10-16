# GCP config
	gcloud init

	gcloud auth configure-docker

	gcloud builds submit --tag gcr.io/[]/my-spleeter-image . 

After the build:
You can verify this by checking the list of images in GCR:
	gcloud container images list --repository=[gcr.io/[PROJECT_ID]](http://gcr.io/%5BPROJECT_ID%5D)


	gcloud run deploy my-spleeter-service [params]

Then:
	gcloud builds submit --config cloudbuild.yaml . # enables layer cache, speeds up docker image building


# Job details

## Minimum requirements

mem: 4GiB
cpu: 2

Evaluar: 8GiB
cpu: 4

y timeout: 15min
retries: 3

## Define env vars on GCP config:

then:
	bucket_name = os.getenv('BUCKET_NAME', 'default-bucket-name')
	stems_number = os.getenv('STEMS_NUMBER', '5')


## Download processed dataset
gsutil -m cp -r \
  "gs://[bucketname]-dataset/output" \
  .


$ mkdir sample_audio/loops           
$ gsutil -m cp -R gs://[bucketname]/output sample_audio/loops/    