# Workshop Visualization

Workshop data should be placed under the `data/workshops` folder. Registration data should be placed under the `data/registrations` folder.

To run the project in Docker, run the following:

```
docker build . -t workshop-visualization && docker run -p 5000:5000 workshop-visualization
```

See the dashboard at [http://localhost:5000](http://localhost:5000).
