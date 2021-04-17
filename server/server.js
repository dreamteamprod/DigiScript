import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import morgan from 'morgan';
import path from 'path';
import winston from './config/winston.js';

winston.info('Starting DigiScript server...!');

const app = express();

app.use(morgan('combined', {stream: winston.stream}));
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(path.resolve(), '../client/dist')));

app.get('/', (req, res) => {
  res.sendFile(path.join(path.resolve(), '../client/dist/index.html'));
});

const port = process.env.PORT || 3080;
app.listen(port, () => {
  console.log(`listening on ${port}`);
});
