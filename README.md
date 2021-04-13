# ECA_App
For the ECA, we want to have the highest possible automation possible. By using this app we can have a centralized gsheet that then provides the infoamtion per person.
That way we don't have to push out credentials over the email. We keep them in the Nutanix Network.

For the container to run:
git clone this repo
cd to the location where you have cloned the repo
docker run --rm --name NAME_OF_THE_TOOL -e validator_password=<VALIDATOR_AREA_PASSWORD> -v ${PWD}/json:/json -v ${PWD}:/code -p 3000:3000 -d wessenstam/lookup_tool
