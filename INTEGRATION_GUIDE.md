# n8n AI Agent Integration Guide

This guide shows how to integrate the AI Container Manager with n8n AI agents to create powerful, isolated environments for AI tasks.

## Basic Integration

### Creating a Container from an AI Agent

In your n8n workflow's Code node:

```javascript
// Function to create a new container
async function createContainer() {
  try {
    const response = await $http.post('http://ai-container-manager:5000/api/containers');
    return response.data;
  } catch (error) {
    console.error('Error creating container:', error);
    throw error;
  }
}

// Main execution
const container = await createContainer();
return container;
```

### Running Commands in the Container

```javascript
// Function to execute a command in a container
async function executeCommand(containerId, command) {
  try {
    const response = await $http.post(
      `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
      { command }
    );
    return response.data;
  } catch (error) {
    console.error('Error executing command:', error);
    throw error;
  }
}

// Get container ID (from previous node or workflow data)
const containerId = items[0].json.id;

// Run a command
const result = await executeCommand(containerId, 'python -c "print(\'Hello from AI agent\')"');
return result;
```

### Deleting a Container

```javascript
// Function to delete a container
async function deleteContainer(containerId) {
  try {
    const response = await $http.delete(
      `http://ai-container-manager:5000/api/containers/${containerId}`
    );
    return response.data;
  } catch (error) {
    console.error('Error deleting container:', error);
    throw error;
  }
}

// Get container ID (from previous node or workflow data)
const containerId = items[0].json.id;

// Delete the container
const result = await deleteContainer(containerId);
return result;
```

### Getting Container Stats

```javascript
// Function to get container stats
async function getContainerStats() {
  try {
    const response = await $http.get('http://ai-container-manager:5000/api/containers/stats');
    return response.data;
  } catch (error) {
    console.error('Error fetching container stats:', error);
    throw error;
  }
}

// Get statistics about all active containers
const stats = await getContainerStats();
return {
  activeCount: stats.active_count,
  expiryHours: stats.expiry_hours,
  oldestContainers: stats.containers.slice(0, 3) // Get the 3 oldest containers
};
```

### Cleaning Up All Containers

```javascript
// Function to clean up all containers
async function cleanupContainers() {
  try {
    const response = await $http.post('http://ai-container-manager:5000/api/containers/cleanup');
    return response.data;
  } catch (error) {
    console.error('Error cleaning up containers:', error);
    throw error;
  }
}

// Delete all active containers
const result = await cleanupContainers();
return {
  message: `Cleaned up ${result.success_count} containers with ${result.fail_count} failures`,
  success: result.success_count,
  failures: result.fail_count
};
```

## AI Agent Workflow Patterns

### Pattern 1: Temporary Container for Single Task

1. Create container
2. Execute task(s)
3. Get results
4. Delete container

```javascript
// Create container
const container = await $http.post('http://ai-container-manager:5000/api/containers');
const containerId = container.data.id;

try {
  // Set up the environment
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'git clone https://github.com/example/repo.git /workspace/repo' }
  );
  
  // Run the task
  const result = await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'cd /workspace/repo && python analyze.py' }
  );
  
  // Return the results
  return { output: result.data.output };
  
} finally {
  // Always clean up the container
  await $http.delete(`http://ai-container-manager:5000/api/containers/${containerId}`);
}
```

### Pattern 2: Persistent Environment with State

1. Create container and store ID
2. Use container across multiple workflow runs
3. Delete container on explicit cleanup or when no longer needed

```javascript
// Get or create container ID
let containerId = await $node.context.get('containerId');

if (!containerId) {
  // No container exists, create one
  const container = await $http.post('http://ai-container-manager:5000/api/containers');
  containerId = container.data.id;
  
  // Store for future use
  await $node.context.set('containerId', containerId);
  
  // Initialize the environment
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'git clone https://github.com/example/repo.git /workspace/repo' }
  );
}

// Run the current task
const result = await $http.post(
  `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
  { command: 'cd /workspace/repo && python process.py --input=' + items[0].json.input }
);

return { containerId, output: result.data.output };
```

### Pattern 3: Multi-Container Parallel Processing

```javascript
// Create multiple containers for parallel processing
async function createContainers(count) {
  const containers = [];
  for (let i = 0; i < count; i++) {
    const container = await $http.post('http://ai-container-manager:5000/api/containers');
    containers.push(container.data);
  }
  return containers;
}

// Process data in parallel across containers
async function processInParallel(containers, tasks) {
  const results = [];
  const promises = tasks.map((task, index) => {
    const containerId = containers[index % containers.length].id;
    return $http.post(
      `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
      { command: `python -c "print('Processing task: ${task}')"` }
    ).then(response => {
      results.push({
        task,
        output: response.data.output,
        container: containerId
      });
    });
  });
  
  await Promise.all(promises);
  return results;
}

// Clean up all containers
async function deleteContainers(containers) {
  // Option 1: Delete containers one by one
  for (const container of containers) {
    await $http.delete(`http://ai-container-manager:5000/api/containers/${container.id}`);
  }
  
  // Option 2: Use the bulk cleanup endpoint instead
  // await $http.post('http://ai-container-manager:5000/api/containers/cleanup');
}

// Main execution
const taskList = items.map(item => item.json.task);
const containers = await createContainers(3); // Create 3 containers

try {
  const results = await processInParallel(containers, taskList);
  return { results };
} finally {
  await deleteContainers(containers);
}
```

## Best Practices for AI Agents

1. **Error Handling**: Always implement proper error handling and container cleanup
2. **Resource Management**: Delete containers when they're no longer needed
3. **Persistence**: Use persistent storage for important data in `/workspace`
4. **Timeouts**: Set appropriate timeouts for long-running tasks
5. **Logging**: Implement logging to track container usage
6. **State Management**: Store container IDs in n8n variables or database

## Example: AI Agent for Data Analysis

```javascript
// This example shows an AI agent that analyzes data using a container

// Parameters from previous nodes
const datasetUrl = items[0].json.datasetUrl;
const analysisType = items[0].json.analysisType;

// Create a container
const container = await $http.post('http://ai-container-manager:5000/api/containers');
const containerId = container.data.id;

try {
  // Set up the environment
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'pip install pandas matplotlib scikit-learn' }
  );
  
  // Download the dataset
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: `curl -o /workspace/dataset.csv "${datasetUrl}"` }
  );
  
  // Create analysis script
  const pythonScript = `
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

# Load the dataset
df = pd.read_csv('/workspace/dataset.csv')

# Perform analysis
if '${analysisType}' == 'clustering':
    # K-means clustering
    kmeans = KMeans(n_clusters=3)
    df['cluster'] = kmeans.fit_predict(df[['feature1', 'feature2']])
    result = df['cluster'].value_counts().to_dict()
elif '${analysisType}' == 'summary':
    # Summary statistics
    result = df.describe().to_dict()
else:
    result = {"error": "Unknown analysis type"}

# Save results
import json
with open('/workspace/results.json', 'w') as f:
    json.dump(result, f)
    
print("Analysis complete!")
  `;
  
  // Save and execute the script
  await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: `echo '${pythonScript}' > /workspace/analyze.py && python /workspace/analyze.py` }
  );
  
  // Get the results
  const resultOutput = await $http.post(
    `http://ai-container-manager:5000/api/containers/${containerId}/exec`,
    { command: 'cat /workspace/results.json' }
  );
  
  // Parse and return the results
  const analysisResults = JSON.parse(resultOutput.data.output);
  return {
    containerId,
    analysisType,
    results: analysisResults
  };
  
} catch (error) {
  return {
    error: true,
    message: error.message
  };
} finally {
  // Clean up the container
  await $http.delete(`http://ai-container-manager:5000/api/containers/${containerId}`);
}
```

For more detailed information and advanced usage, refer to the [full documentation](DOCUMENTATION.md).