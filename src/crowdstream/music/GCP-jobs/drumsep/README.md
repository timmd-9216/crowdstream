Run drumsep as a container. Useful to run in a cloud context or isolating dependencies

# Setup

## GCP config
	gcloud init

	gcloud auth configure-docker

	gcloud builds submit --tag gcr.io/[]/my-drumsep-image . 

After the build:
You can verify this by checking the list of images in GCR:
	gcloud container images list --repository=[gcr.io/[PROJECT_ID]](http://gcr.io/%5BPROJECT_ID%5D)


	gcloud run deploy my-drumsep-service [params]

Then:
	gcloud builds submit --config cloudbuild.yaml . # enables layer cache, speeds up docker image building



# Run
	mkdir -p data/input
	mv [ORIGIN-DRUM-TRACK] data/input/drums.wav
	mkdir data/output
	
	sudo docker run -v $PWD/data:/data --rm drumsep /data/input/drums.wav /data/output/

	Final output will be in data/output/49469ca8/drums/ as:
		bombo.wav
		platillos.wav
		redoblante.wav
		toms.wav
