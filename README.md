# Workshop Visualization

## Deployment 

1. Place a valid .env in the root of the repository. The .env should have the following variables:
- `QUALTRICS_API_TOKEN`: API token for Qualtrics.
- `QUALTRICS_URL_BASE`: Base URL of Qualtrics API.
- `QUALTRICS_SURVEY_ID`: ID of Qualtrics survey.
- `LIBCAL_CLIENT_ID`: Client ID for Libcal API
- `LIBCAL_CLIENT_SECRET`: Client secret for Libcal API
- `HSL_CLIENT_ID`: Client ID for HSL API
- `HSL_CLIENT_SECRET`: Client secret for HSL API

2. Run the project in Docker.

```
docker build . -t workshop-visualization && docker run -p 5000:5000 workshop-visualization
```

3. See the dashboard at [http://localhost:5000](http://localhost:5000).
