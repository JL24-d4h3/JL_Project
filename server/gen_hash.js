const { hash } = require('argon2');

async function generateHashes() {
  const password1 = await hash('Test1234');
  const password2 = await hash('Demo1234');
  
  console.log('testuser (Test1234):', password1);
  console.log('democlient (Demo1234):', password2);
}

generateHashes();
