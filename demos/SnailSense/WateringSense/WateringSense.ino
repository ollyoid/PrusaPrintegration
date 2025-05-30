#define BUFFER_SIZE 600
int readingsBuffer[BUFFER_SIZE]; // Array to hold the readings
int readingsIndex = 0; // Current index in the buffer
long sumOfReadings = 0; // Sum of the readings in the buffer
int readingsCount = 0; // Number of readings added to the buffer
unsigned long lastWateredTime = 0; // Timestamp of the last "Watered" message
const unsigned long cooldownPeriod = 10000; // Cooldown period of 10 seconds (10000 milliseconds)

void setup() {
  // Initialize serial communication at 115200 bits per second:
  Serial.begin(115200);
  
  // Set the resolution to 12 bits (0-4095)
  analogReadResolution(12);

  // Initialize the buffer
  for (int i = 0; i < BUFFER_SIZE; i++) {
    readingsBuffer[i] = 0;
  }
}

void loop() {
  unsigned long currentTime = millis(); // Get the current time
  int analogValue = analogRead(A9); // Read the current value from the sensor

  // Subtract the oldest reading from sumOfReadings
  sumOfReadings -= readingsBuffer[readingsIndex];
  // Add the new reading to the buffer and update the sum
  readingsBuffer[readingsIndex] = analogValue;
  sumOfReadings += analogValue;

  // Update the readings count and index for the circular buffer
  if (readingsCount < BUFFER_SIZE) {
    readingsCount++;
  }
  readingsIndex = (readingsIndex + 1) % BUFFER_SIZE;

  // Calculate the average of the readings in the buffer
  float averageValue = (float)sumOfReadings / readingsCount;
  
  // Compare the current reading to the average and check for a 5% decrease
  // Ensure there's more than one reading for comparison and check if cooldown period has passed
  if (readingsCount > 1 && (currentTime - lastWateredTime) > cooldownPeriod) {
    float percentChange = ((averageValue - analogValue) / averageValue) * 100.0;
    
    // Check if the change is more than 5%
    if (percentChange > 3) {
      Serial.println("Watered");
      lastWateredTime = currentTime; // Update the lastWateredTime to the current time
    }
  }
  Serial.printf("ADC analog value = %d, val1 = 1000, val2 = 3000 \n", analogValue);
  
  delay(100); // Delay in between reads for stability
}