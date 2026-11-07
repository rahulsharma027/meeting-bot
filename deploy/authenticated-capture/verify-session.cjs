// Verify the real bot launch path can use the stored session without joining a meeting.
const {validateLoggedIn} = require('/app/core/meetings/modules/remote-browser/dist/validate.js');

(async () => {
  const {launchBrowser} = await import('/app/core/meetings/services/bot/dist/capture-bridge.js');
  const session = await launchBrowser({
    platform: 'google_meet', authenticated: true,
    userdataS3Path: process.env.BOT_USERDATA_S3_PATH,
    s3Endpoint: process.env.BOT_S3_ENDPOINT, s3Bucket: process.env.BOT_S3_BUCKET,
    s3AccessKey: process.env.BOT_S3_ACCESS_KEY, s3SecretKey: process.env.BOT_S3_SECRET_KEY,
    transcribeEnabled: false, recordingEnabled: false,
  });
  let verified = false;
  try {
    const status = await validateLoggedIn(session.page, 'google');
    if (!status.loggedIn) throw new Error('Stored Google session was not confirmed');
    verified = true;
    console.log('TRANSCRIPTLENS_AUTH_SESSION_VERIFIED');
  } finally {
    if (verified) await session.close();
    else await session.context.close(); // Never publish an unconfirmed profile over the durable copy.
  }
})().then(() => process.exit(0)).catch(() => {
  console.error('Stored-session validation failed; no meeting was joined.');
  process.exit(1);
});
