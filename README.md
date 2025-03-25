# Workshop Visualization

Workshop data is extracted from the libcal API. In the libcal/ folder, place a valid .env to pull workshop data from. Then, run the following command to run the project in Docker.

```
docker build . -t workshop-visualization && docker run -p 5000:5000 workshop-visualization
```

See the dashboard at [http://localhost:5000](http://localhost:5000).
