// Script to get the WSL IP address and update the Vite config
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

try {
  // Get the WSL IP address
  const wslIP = execSync('wsl -e bash -c "ip addr show eth0 | grep -oP \'(?<=inet\\s)\\d+(\\.\\d+){3}\'"').toString().trim();
  console.log(`WSL IP address: ${wslIP}`);

  // Update the .env file
  const envPath = path.join(__dirname, '.env');
  let envContent = '';
  
  try {
    envContent = fs.readFileSync(envPath, 'utf8');
  } catch (err) {
    console.log('No existing .env file, creating a new one');
    envContent = 'VITE_FRONTEND_URL=http://localhost:5173\n';
  }

  // Replace or add the VITE_BACKEND_URL
  if (envContent.includes('VITE_BACKEND_URL=')) {
    envContent = envContent.replace(/VITE_BACKEND_URL=.*$/m, `VITE_BACKEND_URL=http://${wslIP}:8001/api`);
  } else {
    envContent = `VITE_BACKEND_URL=http://${wslIP}:8001/api\n${envContent}`;
  }

  // Write the updated content back to the .env file
  fs.writeFileSync(envPath, envContent);
  console.log(`Updated .env file with WSL IP: ${wslIP}`);

  // Update the vite.config.ts file
  const vitePath = path.join(__dirname, 'vite.config.ts');
  let viteContent = fs.readFileSync(vitePath, 'utf8');

  // Replace the proxy target
  viteContent = viteContent.replace(
    /target: ['"]http:\/\/[^:]+:8001['"]/,
    `target: 'http://${wslIP}:8001'`
  );

  // Write the updated content back to the vite.config.ts file
  fs.writeFileSync(vitePath, viteContent);
  console.log(`Updated vite.config.ts with WSL IP: ${wslIP}`);

  console.log('Configuration updated successfully!');
} catch (error) {
  console.error('Error:', error.message);
}
