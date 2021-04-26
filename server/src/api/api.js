import express from 'express';

const router = new express.Router();

router.get('/test', (req, res) => {
  res.status(200);
  res.json({'status': 'success'});
});

export default router;
