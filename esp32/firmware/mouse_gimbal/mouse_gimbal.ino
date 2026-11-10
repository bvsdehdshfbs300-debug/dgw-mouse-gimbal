/*
  ESP32-S3 mouse controlled two-axis stepper pulse output.

  Serial commands at 115200:
    X 100      move X axis by +100 step pulses
    Y -80      move Y axis by -80 step pulses
    M 20 -10   move both axes, interleaved
    P 400      set half-period in microseconds
    E 1        enable motors if EN pins are wired
    E 0        disable motors if EN pins are wired
    ?          print help
*/

static const int X_STEP_PIN = 7;
static const int X_DIR_PIN  = 15;
static const int X_EN_PIN   = 16;

static const int Y_STEP_PIN = 4;
static const int Y_DIR_PIN  = 5;
static const int Y_EN_PIN   = 6;

static const bool USE_ENABLE_PINS = false;
static const bool ENABLE_ACTIVE_LEVEL = HIGH;

static const bool X_DIR_POSITIVE_LEVEL = HIGH;
static const bool Y_DIR_POSITIVE_LEVEL = HIGH;

static const unsigned int MIN_STEP_HALF_PERIOD_US = 80;
static unsigned int stepHalfPeriodUs = 500;

static String line;

void writeEnable(bool enabled) {
  if (!USE_ENABLE_PINS) {
    return;
  }

  const int level = enabled ? ENABLE_ACTIVE_LEVEL : !ENABLE_ACTIVE_LEVEL;
  digitalWrite(X_EN_PIN, level);
  digitalWrite(Y_EN_PIN, level);
}

void setDirection(int dirPin, bool positive, bool positiveLevel) {
  digitalWrite(dirPin, positive == positiveLevel ? HIGH : LOW);
  delayMicroseconds(5);
}

void pulsePin(int stepPin) {
  digitalWrite(stepPin, HIGH);
  delayMicroseconds(stepHalfPeriodUs);
  digitalWrite(stepPin, LOW);
  delayMicroseconds(stepHalfPeriodUs);
}

void moveAxis(int stepPin, int dirPin, bool positiveLevel, long steps) {
  if (steps == 0) {
    return;
  }

  setDirection(dirPin, steps > 0, positiveLevel);
  unsigned long count = labs(steps);
  for (unsigned long i = 0; i < count; ++i) {
    pulsePin(stepPin);
  }
}

void moveBoth(long xSteps, long ySteps) {
  if (xSteps == 0 && ySteps == 0) {
    return;
  }

  setDirection(X_DIR_PIN, xSteps >= 0, X_DIR_POSITIVE_LEVEL);
  setDirection(Y_DIR_PIN, ySteps >= 0, Y_DIR_POSITIVE_LEVEL);

  unsigned long ax = labs(xSteps);
  unsigned long ay = labs(ySteps);
  unsigned long major = max(ax, ay);

  unsigned long errX = 0;
  unsigned long errY = 0;

  for (unsigned long i = 0; i < major; ++i) {
    bool pulseX = false;
    bool pulseY = false;

    errX += ax;
    if (errX >= major) {
      errX -= major;
      pulseX = ax > 0;
    }

    errY += ay;
    if (errY >= major) {
      errY -= major;
      pulseY = ay > 0;
    }

    if (pulseX) {
      digitalWrite(X_STEP_PIN, HIGH);
    }
    if (pulseY) {
      digitalWrite(Y_STEP_PIN, HIGH);
    }

    delayMicroseconds(stepHalfPeriodUs);

    if (pulseX) {
      digitalWrite(X_STEP_PIN, LOW);
    }
    if (pulseY) {
      digitalWrite(Y_STEP_PIN, LOW);
    }

    delayMicroseconds(stepHalfPeriodUs);
  }
}

void printHelp() {
  Serial.println(F("OK mouse_gimbal"));
  Serial.println(F("Commands: X n | Y n | M x y | P us | E 0/1 | ?"));
}

void handleCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) {
    return;
  }

  char op = cmd.charAt(0);
  op = (char)toupper(op);

  if (op == '?') {
    printHelp();
    return;
  }

  char buffer[96];
  cmd.toCharArray(buffer, sizeof(buffer));

  if (op == 'X') {
    long steps = atol(buffer + 1);
    moveAxis(X_STEP_PIN, X_DIR_PIN, X_DIR_POSITIVE_LEVEL, steps);
    Serial.println(F("OK"));
  } else if (op == 'Y') {
    long steps = atol(buffer + 1);
    moveAxis(Y_STEP_PIN, Y_DIR_PIN, Y_DIR_POSITIVE_LEVEL, steps);
    Serial.println(F("OK"));
  } else if (op == 'M') {
    char *p = buffer + 1;
    long xSteps = strtol(p, &p, 10);
    long ySteps = strtol(p, &p, 10);
    moveBoth(xSteps, ySteps);
    Serial.println(F("OK"));
  } else if (op == 'P') {
    long period = atol(buffer + 1);
    if (period < (long)MIN_STEP_HALF_PERIOD_US) {
      period = MIN_STEP_HALF_PERIOD_US;
    }
    stepHalfPeriodUs = (unsigned int)period;
    Serial.print(F("OK P "));
    Serial.println(stepHalfPeriodUs);
  } else if (op == 'E') {
    long enabled = atol(buffer + 1);
    writeEnable(enabled != 0);
    Serial.println(F("OK"));
  } else {
    Serial.println(F("ERR unknown command"));
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(10);

  pinMode(X_STEP_PIN, OUTPUT);
  pinMode(X_DIR_PIN, OUTPUT);
  pinMode(X_EN_PIN, OUTPUT);

  pinMode(Y_STEP_PIN, OUTPUT);
  pinMode(Y_DIR_PIN, OUTPUT);
  pinMode(Y_EN_PIN, OUTPUT);

  digitalWrite(X_STEP_PIN, LOW);
  digitalWrite(Y_STEP_PIN, LOW);
  writeEnable(true);

  printHelp();
}

void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      handleCommand(line);
      line = "";
    } else if (line.length() < 90) {
      line += c;
    }
  }
}
