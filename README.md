# Workshop Visualization

Workshop data should be placed under the `data/workshops` folder. Registration data should be placed under the `data/registrations` folder.

To run the project in Docker, run the following:

```
docker build . -t workshop-visualization && docker run workshop-visualization -p 5000:5000
```

See the dashboard at [http://localhost:5000](http://localhost:5000).
