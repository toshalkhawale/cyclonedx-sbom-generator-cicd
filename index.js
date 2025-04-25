const express = require('express');
const _ = require('lodash');
const axios = require('axios');

const app = express();
const port = 3000;

app.get('/', async (req, res) => {
  const data = {
    message: 'Hello World!',
    timestamp: new Date(),
    randomValue: _.random(1, 100)
  };
  
  try {
    const response = await axios.get('https://jsonplaceholder.typicode.com/todos/1');
    data.todo = response.data;
  } catch (error) {
    data.error = 'Failed to fetch todo';
  }
  
  res.json(data);
});

app.listen(port, () => {
  console.log(`Sample app listening at http://localhost:${port}`);
});
