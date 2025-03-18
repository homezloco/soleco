const fs = require('fs');
const path = require('path');

try {
  const envPath = path.join(__dirname, '.env');
  const envContent = fs.readFileSync(envPath, 'utf8');
  console.log('Current .env file content:');
  console.log(envContent);
} catch (error) {
  console.error('Error reading .env file:', error);
}
