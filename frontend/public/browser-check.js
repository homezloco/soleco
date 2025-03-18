// Browser compatibility and ad blocker detection script
(function() {
  console.log('Running browser compatibility check...');
  
  // Check for ad blockers
  const testAdBlocker = () => {
    return new Promise((resolve) => {
      const testElement = document.createElement('div');
      testElement.innerHTML = '&nbsp;';
      testElement.className = 'adsbox';
      testElement.style.position = 'absolute';
      testElement.style.opacity = '0';
      document.body.appendChild(testElement);
      
      setTimeout(() => {
        const isBlocked = testElement.offsetHeight === 0;
        document.body.removeChild(testElement);
        resolve(isBlocked);
      }, 100);
    });
  };
  
  // Check for network request blocking
  const testNetworkBlocking = () => {
    return new Promise((resolve) => {
      const xhr = new XMLHttpRequest();
      xhr.open('GET', '/api/test-connection');
      xhr.timeout = 5000;
      
      xhr.onload = () => resolve(false); // Not blocked
      xhr.onerror = () => resolve(true); // Blocked
      xhr.ontimeout = () => resolve(true); // Likely blocked
      
      try {
        xhr.send();
      } catch (e) {
        resolve(true); // Error sending request, likely blocked
      }
    });
  };
  
  // Run tests and display results
  const runTests = async () => {
    try {
      const adBlockerDetected = await testAdBlocker();
      const networkBlockingDetected = await testNetworkBlocking();
      
      console.log('Ad blocker detected:', adBlockerDetected);
      console.log('Network request blocking detected:', networkBlockingDetected);
      
      // Add results to window object for access from React
      window.browserCheckResults = {
        adBlockerDetected,
        networkBlockingDetected,
        timestamp: new Date().toISOString()
      };
      
      // Dispatch event for React to listen to
      window.dispatchEvent(new CustomEvent('browserCheckComplete', { 
        detail: window.browserCheckResults 
      }));
      
      // Create UI notification if issues detected
      if (adBlockerDetected || networkBlockingDetected) {
        const notification = document.createElement('div');
        notification.style.position = 'fixed';
        notification.style.top = '0';
        notification.style.left = '0';
        notification.style.right = '0';
        notification.style.backgroundColor = '#f8d7da';
        notification.style.color = '#721c24';
        notification.style.padding = '10px';
        notification.style.textAlign = 'center';
        notification.style.zIndex = '9999';
        notification.style.fontFamily = 'Arial, sans-serif';
        notification.innerHTML = `
          <strong>Warning:</strong> We've detected that your browser might be blocking API requests. 
          This could be caused by an ad blocker or privacy extension. 
          Please disable these extensions for this site to ensure full functionality.
          <button id="dismiss-notification" style="margin-left: 10px; padding: 2px 8px; cursor: pointer;">Dismiss</button>
        `;
        
        document.body.appendChild(notification);
        
        document.getElementById('dismiss-notification').addEventListener('click', () => {
          document.body.removeChild(notification);
        });
      }
    } catch (error) {
      console.error('Error running browser compatibility tests:', error);
    }
  };
  
  // Run tests when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runTests);
  } else {
    runTests();
  }
})();
