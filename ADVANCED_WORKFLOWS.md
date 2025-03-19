# Advanced n8n AI Container Manager Workflows

This document outlines advanced integration patterns and workflow ideas for the AI Container Manager.

## 1. Agent Handoff Workflow

This pattern allows different n8n workflows to collaborate using the same container.

```javascript
// Workflow 1: Create container and prepare environment
async function createAndPrepareContainer() {
  // Create a container
  const container = await $http.post('http://ai-container-manager:5000/api/containers');
  const containerId = container.data.id;
  
  // Save to workflow variable store for future workflows
  await $node.context.set('shared_container_id', containerId);
  
  // Initialize environment (install tools, clone repo, etc.)
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'git clone https://github.com/example/repo.git /workspace/repo' }
  );
  
  // Trigger next workflow (webhook, event, etc.)
  await $http.post(
    'https://your-n8n-instance/webhook/workflow-2',
    { containerId }
  );
  
  return { containerId, message: 'Container created and handed off to Workflow 2' };
}
```

## 2. Specialized Processing Chain

Chain multiple workflows together to create a specialized processing pipeline.

1. **Data Acquisition Workflow**
   - Creates container
   - Downloads and validates input data
   - Triggers Processing Workflow

2. **Data Processing Workflow**
   - Performs computation on data
   - Transforms results
   - Triggers Results Workflow

3. **Results Extraction Workflow**
   - Extracts formatted results
   - Stores or sends results to destination
   - Cleans up container

## 3. Stateful Multi-Session AI

Create intelligent agents that maintain state between interactions.

```javascript
// Retrieve existing container or create a new one
async function getOrCreateContainer(userId) {
  // Check if we have a container for this user
  let containerId = await $node.context.get(`container_${userId}`);
  
  if (!containerId) {
    // Create a new container for this user
    const container = await $http.post('http://ai-container-manager:5000/api/containers');
    containerId = container.data.id;
    
    // Save ID for future use
    await $node.context.set(`container_${userId}`, containerId);
    
    // Initialize AI environment
    await $http.post(
      `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
      { command: 'pip install torch transformers' }
    );
    
    // Set up initial state
    await $http.post(
      `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
      { command: 'echo "[]" > /workspace/conversation_history.json' }
    );
  }
  
  // Return the container ID
  return containerId;
}

// Add user message to conversation history
async function processUserMessage(containerId, userMessage) {
  // Escape the message for command line use
  const escapedMessage = userMessage.replace(/"/g, '\\"');
  
  // Add message to history
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: `python -c "import json; history=json.load(open('/workspace/conversation_history.json')); history.append({'role': 'user', 'content': \\"${escapedMessage}\\"}); json.dump(history, open('/workspace/conversation_history.json', 'w'))"` }
  );
  
  // Generate AI response
  const result = await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'python /workspace/generate_response.py' }
  );
  
  return result.data.output;
}
```

## 4. Background Processing with Status Tracking

Run long-running tasks in the background and check their status periodically.

```javascript
// Start a long-running job
async function startBackgroundJob(containerId, jobConfig) {
  // Write job config to container
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: `echo '${JSON.stringify(jobConfig)}' > /workspace/job_config.json` }
  );
  
  // Start the job in the background
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'nohup python /workspace/run_job.py > /workspace/job.log 2>&1 &' }
  );
  
  return { containerId, status: 'started' };
}

// Check job status
async function checkJobStatus(containerId) {
  // Check if the job process is still running
  const processCheck = await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'ps aux | grep run_job.py | grep -v grep || echo "not running"' }
  );
  
  // Check for status file that the job creates
  const statusCheck = await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'cat /workspace/job_status.json 2>/dev/null || echo "{\"status\": \"unknown\"}"' }
  );
  
  // Parse the status
  let status;
  try {
    status = JSON.parse(statusCheck.data.output);
  } catch (e) {
    status = { status: 'error', message: 'Could not parse status' };
  }
  
  return {
    containerId,
    isRunning: !processCheck.data.output.includes('not running'),
    ...status
  };
}
```

## 5. Dynamic Container Pools

Create a pool of containers that scales based on demand.

```javascript
// Get active container pool
async function getContainerPool() {
  // Try to get existing pool
  let pool = await $node.context.get('container_pool') || [];
  
  // Query each container to make sure it's still valid
  const validPool = [];
  for (const containerId of pool) {
    try {
      // Try to ping the container
      const result = await $http.post(
        `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
        { command: 'echo "ping"' }
      );
      
      if (result.data.output.includes('ping')) {
        validPool.push(containerId);
      }
    } catch (e) {
      // Container is no longer valid
      console.log(`Container ${containerId} is no longer valid`);
    }
  }
  
  // Update pool
  await $node.context.set('container_pool', validPool);
  return validPool;
}

// Scale pool to target size
async function scalePoolToSize(targetSize) {
  // Get current pool
  const pool = await getContainerPool();
  
  // Scale up
  if (pool.length < targetSize) {
    for (let i = pool.length; i < targetSize; i++) {
      // Create a new container
      const container = await $http.post('http://ai-container-manager:5000/api/containers');
      
      // Initialize it
      await $http.post(
        `http://ai-container-manager:5000/api/containers/${container.data.id}/exec`,
        { command: 'echo "Container initialized" > /workspace/init.log' }
      );
      
      // Add to pool
      pool.push(container.data.id);
    }
  }
  
  // Scale down
  if (pool.length > targetSize) {
    const containersToRemove = pool.slice(targetSize);
    
    // Remove each container
    for (const containerId of containersToRemove) {
      await $http.delete(`http://ai-container-manager:5000/api/containers/${containerId}`);
      pool.pop();
    }
  }
  
  // Update stored pool
  await $node.context.set('container_pool', pool);
  
  return {
    poolSize: pool.length,
    containers: pool
  };
}

// Get container from pool
async function getContainerFromPool() {
  const pool = await getContainerPool();
  
  if (pool.length === 0) {
    // No containers available, create one
    const container = await $http.post('http://ai-container-manager:5000/api/containers');
    pool.push(container.data.id);
    await $node.context.set('container_pool', pool);
    return container.data.id;
  }
  
  // Return the first container (round-robin)
  const containerId = pool.shift();
  pool.push(containerId);
  await $node.context.set('container_pool', pool);
  
  return containerId;
}
```

## 6. AI Training Coordination

Use containers to coordinate AI model training and evaluation.

```javascript
// Start training a model
async function startModelTraining(hyperparameters) {
  // Create a container for training
  const container = await $http.post('http://ai-container-manager:5000/api/containers');
  const containerId = container.data.id;
  
  // Install dependencies
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'pip install torch scikit-learn pandas matplotlib' }
  );
  
  // Create training script with hyperparameters
  const trainingScript = `
import torch
import pandas as pd
from sklearn.model_selection import train_test_split
import json

# Load hyperparameters
hyperparameters = json.loads("""${JSON.stringify(hyperparameters)}""")

# Training code here
learning_rate = hyperparameters.get('learning_rate', 0.01)
batch_size = hyperparameters.get('batch_size', 32)
epochs = hyperparameters.get('epochs', 10)

# Mock training loop
import time
for epoch in range(epochs):
    loss = 1.0 - (epoch / epochs) * 0.9  # Mock decreasing loss
    accuracy = 0.5 + (epoch / epochs) * 0.4  # Mock increasing accuracy
    
    # Save metrics
    with open('/workspace/metrics.json', 'w') as f:
        json.dump({
            'epoch': epoch + 1,
            'total_epochs': epochs,
            'loss': loss,
            'accuracy': accuracy,
            'status': 'training'
        }, f)
    
    # Simulate training time
    time.sleep(5)

# Save final metrics
with open('/workspace/metrics.json', 'w') as f:
    json.dump({
        'epoch': epochs,
        'total_epochs': epochs,
        'loss': 0.1,
        'accuracy': 0.9,
        'status': 'complete'
    }, f)
  `;
  
  // Save and execute the training script
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: `echo '${trainingScript.replace(/'/g, "'\\''")}' > /workspace/train.py` }
  );
  
  // Start training in the background
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'nohup python /workspace/train.py > /workspace/training.log 2>&1 &' }
  );
  
  return {
    containerId,
    status: 'training_started',
    hyperparameters
  };
}

// Check training status
async function checkTrainingStatus(containerId) {
  try {
    // Get training metrics
    const result = await $http.post(
      `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
      { command: 'cat /workspace/metrics.json 2>/dev/null || echo "{\"status\": \"not_started\"}"' }
    );
    
    // Parse metrics
    const metrics = JSON.parse(result.data.output);
    
    return {
      containerId,
      ...metrics
    };
  } catch (e) {
    return {
      containerId,
      status: 'error',
      message: 'Failed to get training status'
    };
  }
}
```

## 7. Self-Maintaining Container Networks

Create a network of containers that monitor and maintain each other.

```javascript
// Initialize monitoring network
async function initMonitoringNetwork(containerCount) {
  // Create containers
  const containers = [];
  for (let i = 0; i < containerCount; i++) {
    const container = await $http.post('http://ai-container-manager:5000/api/containers');
    containers.push(container.data);
  }
  
  // Set up monitoring script on each container
  for (const container of containers) {
    // Create monitoring script
    const monitorScript = `
import time
import json
import os
import requests

# Other container IDs to monitor
container_ids = ${JSON.stringify(containers.map(c => c.id).filter(id => id !== container.id))}

def check_container(container_id):
    try:
        response = requests.post(
            f'http://ai-container-manager:5000/api/containers/{container_id}/exec',
            json={'command': 'echo "health_check"'},
            timeout=5
        )
        return response.status_code == 200 and 'health_check' in response.json().get('output', '')
    except Exception as e:
        return False

# Monitor loop
while True:
    status = {id: check_container(id) for id in container_ids}
    
    # Save status
    with open('/workspace/monitor_status.json', 'w') as f:
        json.dump({
            'container_id': '${container.id}',
            'timestamp': time.time(),
            'status': status
        }, f)
    
    time.sleep(60)  # Check every minute
    `;
    
    // Save and execute the monitor script
    await $http.post(
      `http://ai-container-manager:5000/api/containers/${container.id}/exec`,
      { command: 'pip install requests' }
    );
    
    await $http.post(
      `http://ai-container-manager:5000/api/containers/${container.id}/exec`,
      { command: `echo '${monitorScript.replace(/'/g, "'\\''")}' > /workspace/monitor.py` }
    );
    
    // Start monitoring in the background
    await $http.post(
      `http://ai-container-manager:5000/api/containers/${container.id}/exec`,
      { command: 'nohup python /workspace/monitor.py > /workspace/monitor.log 2>&1 &' }
    );
  }
  
  // Save container IDs
  await $node.context.set('monitor_network', containers.map(c => c.id));
  
  return {
    networkSize: containers.length,
    containers: containers.map(c => c.id)
  };
}

// Get monitoring network status
async function getNetworkStatus() {
  // Get container IDs
  const containerIds = await $node.context.get('monitor_network') || [];
  
  // Get status from each container
  const statuses = [];
  for (const containerId of containerIds) {
    try {
      const result = await $http.post(
        `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
        { command: 'cat /workspace/monitor_status.json 2>/dev/null || echo "{}"' }
      );
      
      if (result.data.output && result.data.output !== '{}') {
        statuses.push(JSON.parse(result.data.output));
      }
    } catch (e) {
      // This container might be down
      console.log(`Container ${containerId} may be down: ${e.message}`);
    }
  }
  
  return {
    networkSize: containerIds.length,
    statuses
  };
}
```

## 8. Auto-Scaling Scientific Workflow

Create a scientific computing workflow that automatically scales based on input data size.

```javascript
// Process scientific data with auto-scaling
async function processScientificData(datasetSize) {
  // Determine optimal container count based on dataset size
  const containerCount = Math.max(1, Math.min(10, Math.ceil(datasetSize / 1000)));
  
  // Create containers
  const containers = [];
  for (let i = 0; i < containerCount; i++) {
    const container = await $http.post('http://ai-container-manager:5000/api/containers');
    containers.push(container.data);
    
    // Set up environment
    await $http.post(
      `http://ai-container-manager:5000/api/containers/${container.data.id}/exec`,
      { command: 'pip install numpy scipy matplotlib' }
    );
  }
  
  // Distribute work
  const chunkSize = Math.ceil(datasetSize / containerCount);
  const results = [];
  
  // Process in parallel
  const processPromises = containers.map((container, index) => {
    const start = index * chunkSize;
    const end = Math.min(start + chunkSize, datasetSize);
    
    return $http.post(
      `http://ai-container-manager:5000/api/containers/${container.id}/exec`,
      { 
        command: `python -c "
import numpy as np
import json

# Generate mock data
data = np.random.rand(${end - start}, 5)  # 5 features
processed = np.mean(data, axis=0).tolist()

# Save results
with open('/workspace/results.json', 'w') as f:
    json.dump({'chunk': [${start}, ${end}], 'result': processed}, f)
"` 
      }
    ).then(() => {
      // Get results
      return $http.post(
        `http://ai-container-manager:5000/api/containers/${container.id}/exec`,
        { command: 'cat /workspace/results.json' }
      );
    }).then(response => {
      return JSON.parse(response.data.output);
    });
  });
  
  // Wait for all processing to complete
  const chunkResults = await Promise.all(processPromises);
  
  // Combine results
  const combinedResult = {
    datasetSize,
    containerCount,
    results: chunkResults
  };
  
  // Clean up containers
  for (const container of containers) {
    await $http.delete(`http://ai-container-manager:5000/api/containers/${container.id}`);
  }
  
  return combinedResult;
}
```

## 9. AI Container Orchestration with n8n

```javascript
// Simple container orchestrator that manages a set of containers
class ContainerOrchestrator {
  constructor() {
    this.containersKey = 'orchestrator_containers';
  }
  
  // Get all managed containers
  async getContainers() {
    return await $node.context.get(this.containersKey) || [];
  }
  
  // Save container list
  async saveContainers(containers) {
    await $node.context.set(this.containersKey, containers);
  }
  
  // Create a new container
  async createContainer(purpose) {
    const container = await $http.post('http://ai-container-manager:5000/api/containers');
    
    // Add metadata
    const containerData = {
      ...container.data,
      purpose,
      created: Date.now(),
      lastUsed: Date.now()
    };
    
    // Add to managed containers
    const containers = await this.getContainers();
    containers.push(containerData);
    await this.saveContainers(containers);
    
    return containerData;
  }
  
  // Get container by purpose
  async getContainerByPurpose(purpose) {
    const containers = await this.getContainers();
    const container = containers.find(c => c.purpose === purpose);
    
    if (container) {
      // Update last used
      container.lastUsed = Date.now();
      await this.saveContainers(containers);
      return container;
    }
    
    // No container found, create one
    return await this.createContainer(purpose);
  }
  
  // Delete a container
  async deleteContainer(containerId) {
    // Remove from the manager
    let containers = await this.getContainers();
    containers = containers.filter(c => c.id !== containerId);
    await this.saveContainers(containers);
    
    // Delete the actual container
    return await $http.delete(`http://ai-container-manager:5000/api/containers/${containerId}`);
  }
  
  // Cleanup old containers
  async cleanupOldContainers(maxAgeHours = 24) {
    const containers = await this.getContainers();
    const now = Date.now();
    const maxAgeMs = maxAgeHours * 60 * 60 * 1000;
    
    const toDelete = [];
    const remaining = [];
    
    // Identify old containers
    for (const container of containers) {
      if (now - container.lastUsed > maxAgeMs) {
        toDelete.push(container);
      } else {
        remaining.push(container);
      }
    }
    
    // Delete old containers
    for (const container of toDelete) {
      try {
        await $http.delete(`http://ai-container-manager:5000/api/containers/${container.id}`);
      } catch (e) {
        console.log(`Failed to delete container ${container.id}: ${e.message}`);
      }
    }
    
    // Update container list
    await this.saveContainers(remaining);
    
    return {
      deleted: toDelete.length,
      remaining: remaining.length
    };
  }
}

// Example usage
async function main() {
  const orchestrator = new ContainerOrchestrator();
  
  // Get or create a container for NLP processing
  const nlpContainer = await orchestrator.getContainerByPurpose('nlp');
  
  // Install NLP libraries if needed
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${nlpContainer.id}/exec`,
    { command: 'pip list | grep -q "^nltk " || pip install nltk' }
  );
  
  // Process some text
  const result = await $http.post(
    `http://ai-container-manager:5000/api/containers/${nlpContainer.id}/exec`,
    { command: 'python -c "import nltk; nltk.download(\'punkt\', quiet=True); print(nltk.tokenize.word_tokenize(\'Hello world, this is a test.\'))"' }
  );
  
  return {
    container: nlpContainer,
    result: result.data.output
  };
}
```

## 10. Language-Specific AI Development Environments

Create specialized containers for different programming languages and AI frameworks.

```javascript
// Create a PyTorch development environment
async function createPyTorchEnvironment() {
  // Create container
  const container = await $http.post('http://ai-container-manager:5000/api/containers');
  const containerId = container.data.id;
  
  // Set up PyTorch environment
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'pip install torch torchvision torchaudio matplotlib numpy pandas jupyter' }
  );
  
  // Clone PyTorch examples
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'git clone https://github.com/pytorch/examples.git /workspace/pytorch-examples' }
  );
  
  return {
    containerId,
    type: 'pytorch',
    ready: true
  };
}

// Create a TensorFlow development environment
async function createTensorFlowEnvironment() {
  // Create container
  const container = await $http.post('http://ai-container-manager:5000/api/containers');
  const containerId = container.data.id;
  
  // Set up TensorFlow environment
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'pip install tensorflow tensorflow-datasets matplotlib numpy pandas jupyter' }
  );
  
  // Clone TensorFlow examples
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'git clone https://github.com/tensorflow/examples.git /workspace/tensorflow-examples' }
  );
  
  return {
    containerId,
    type: 'tensorflow',
    ready: true
  };
}

// Create a JavaScript Node.js AI environment
async function createNodeJsAIEnvironment() {
  // Create container
  const container = await $http.post('http://ai-container-manager:5000/api/containers');
  const containerId = container.data.id;
  
  // Set up Node.js environment
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'apt-get update && apt-get install -y nodejs npm' }
  );
  
  // Install TensorFlow.js
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'mkdir -p /workspace/node-ai && cd /workspace/node-ai && npm init -y && npm install @tensorflow/tfjs @tensorflow/tfjs-node' }
  );
  
  // Create example script
  const exampleScript = `
const tf = require('@tensorflow/tfjs-node');

// Simple model
const model = tf.sequential();
model.add(tf.layers.dense({units: 1, inputShape: [1]}));
model.compile({loss: 'meanSquaredError', optimizer: 'sgd'});

// Generate some synthetic data
const xs = tf.tensor2d(Array.from({length: 100}, (_, i) => i / 100), [100, 1]);
const ys = tf.tensor2d(Array.from({length: 100}, (_, i) => i / 50), [100, 1]);

// Train the model
async function train() {
  await model.fit(xs, ys, {
    epochs: 100,
    callbacks: {
      onEpochEnd: (epoch, logs) => {
        console.log(\`Epoch \${epoch}: loss = \${logs.loss}\`);
      }
    }
  });
  
  // Make a prediction
  const output = model.predict(tf.tensor2d([0.5], [1, 1]));
  console.log('Prediction for 0.5:');
  output.print();
}

train();
  `;
  
  // Save the example script
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: `echo '${exampleScript.replace(/'/g, "'\\''")}' > /workspace/node-ai/example.js` }
  );
  
  return {
    containerId,
    type: 'nodejs-ai',
    ready: true
  };
}
```