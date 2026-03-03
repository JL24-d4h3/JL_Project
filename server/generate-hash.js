import bcrypt from 'bcrypt';

const password = 'admin123';
const saltRounds = 10;

bcrypt.hash(password, saltRounds, (err, hash) => {
  if (err) {
    console.error('Error:', err);
    process.exit(1);
  }
  console.log('Password:', password);
  console.log('Hash:', hash);
  console.log('\nUpdate command:');
  console.log(`UPDATE users SET password_hash = '${hash}' WHERE username = 'admin';`);
  process.exit(0);
});
