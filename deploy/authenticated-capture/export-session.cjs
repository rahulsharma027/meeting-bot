// Use upstream's auth-essential subset exporter; never print profile contents.
const fs = require('node:fs');
const { spawnSync } = require('node:child_process');

try {
  process.umask(0o077);
  if (fs.existsSync('/state/exported.json')) {
    console.log('The sign-in session was already exported; the stored session was preserved.');
    process.exit(0);
  }
  const receipt = JSON.parse(fs.readFileSync('/profile/login-confirmed.json', 'utf8'));
  if (receipt.platform !== 'google' || receipt.image_version !== 'v0.12.28') {
    throw new Error('A compatible confirmed Google sign-in is required');
  }
  // Child output stays private: only its bounded success summary is returned.
  const code = `
    const {execFileSync}=require('node:child_process');
    const {syncBrowserDataToS3}=require('/app/core/meetings/modules/remote-browser/dist/session-store.js');
    const n=syncBrowserDataToS3({
      userdataS3Path:process.env.BOT_USERDATA_S3_PATH,
      s3Endpoint:process.env.BOT_S3_ENDPOINT, s3Bucket:process.env.BOT_S3_BUCKET,
      s3AccessKey:process.env.BOT_S3_ACCESS_KEY, s3SecretKey:process.env.BOT_S3_SECRET_KEY
    }, '/profile/browser');
    if(n===0)process.exit(1);
    const env={...process.env,AWS_ACCESS_KEY_ID:process.env.BOT_S3_ACCESS_KEY,
      AWS_SECRET_ACCESS_KEY:process.env.BOT_S3_SECRET_KEY,AWS_DEFAULT_REGION:'us-east-1',
      AWS_EC2_METADATA_DISABLED:'true'};
    for(const name of ['Local State','Default/Cookies']){
      const metadata=JSON.parse(execFileSync('aws',['s3api','head-object',
        '--bucket',process.env.BOT_S3_BUCKET,
        '--key',process.env.BOT_USERDATA_S3_PATH+'/browser-data/'+name,
        '--endpoint-url',process.env.BOT_S3_ENDPOINT],{env,encoding:'utf8',timeout:15000}));
      if(!(metadata.ContentLength>0))process.exit(1);
    }
    process.stdout.write('TRANSCRIPTLENS_SESSION_ITEMS='+n+'\\n');
  `;
  const result = spawnSync(process.execPath, ['-e', code], {
    env: process.env, encoding: 'utf8', timeout: 240000, maxBuffer: 1024 * 1024,
  });
  const match = result.stdout?.match(/^TRANSCRIPTLENS_SESSION_ITEMS=(\d+)$/m);
  if (result.error || result.status !== 0 || !match) {
    throw new Error('The local session export did not complete');
  }
  fs.writeFileSync('/state/exported.json', JSON.stringify({
    exported_at: new Date().toISOString(), auth_essential_items: Number(match[1]),
    mandatory_objects_checked: true,
  }), {flag: 'wx', mode: 0o600});
  console.log(`Saved ${Number(match[1])} auth-essential items to local scoped userdata storage.`);
} catch {
  console.error('Session export failed. The original sign-in profile was retained.');
  process.exitCode = 1;
}
