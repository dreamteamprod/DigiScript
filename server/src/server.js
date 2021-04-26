import {Command} from 'commander/esm.mjs';
import fs from 'fs';
import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import morgan from 'morgan';
import connect from 'connect-history-api-fallback';
import path from 'path';
import winston from './logging/winston.js';
import api from './api/api.js';

// Command line argument parsing
const program = new Command();
program.version('0.0.1');
program.requiredOption('--config <value>', 'Path to server config file');

program.parse(process.argv);
const options = program.opts();

winston.debug(`Starting with command line arguments: ` +
              `${JSON.stringify(options)}`);
winston.info('Starting DigiScript server...!');

// Config parsing
winston.debug(`Loding config file from ${options.config}`);
const rawConfig = fs.readFileSync(options.config);
const config = JSON.parse(rawConfig);
const port = config.port || 3080;


// Server stuff below this line
const app = express();

app.use(morgan('combined', {stream: winston.stream}));
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(path.resolve(), '../client/dist')));
const historyMiddleware = connect({
  disableDotRule: true,
  verbose: true,
  logger: winston.debug,
});
app.use((req, res, next) => {
  if (req.path.startsWith('/api/')) {
    next();
  } else {
    historyMiddleware(req, res, next);
  }
});
app.use(express.static(path.join(path.resolve(), '../client/dist')));

app.use('/api', api);

app.get('/', (req, res) => {
  res.sendFile(path.join(path.resolve(), '../client/dist/index.html'));
});

app.listen(port, () => {
  winston.info(`Server listening on port ${port}`);
});
