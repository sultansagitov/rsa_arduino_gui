#include <Arduino.h>

struct PublicKey {
    int e;
    int n;
};

struct PrivateKey {
    int d;
    int n;
};

int gcd(int a, int b) {
    while (b != 0) {
        int temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

// (base^exp) % mod
long long mod_exp(long long base, long long exp, long long mod) {
    long long result = 1;
    base = base % mod;
    while (exp > 0) {
        if (exp % 2 == 1) {
            result = (result * base) % mod;
        }
        exp = exp >> 1;
        base = (base * base) % mod;
    }
    return result;
}

// e * d % phi = 1 -> d
int mod_inverse(int e, int phi) {
    int m0 = phi;
    int y = 0, x = 1;
 
    if (phi == 1)
        return 0;
 
    while (e > 1) {
        int q = e / phi;
        int t = phi;
        phi = e % phi;
        e = t;
        t = y;
        y = x - q * y;
        x = t;
    }
 
    if (x < 0)
        x += m0;
 
    return x;
}

bool is_prime(int num) {
    if (num <= 1) return false;
    if (num == 2) return true;
    if (num % 2 == 0) return false;
    
    for (int i = 3; i * i <= num; i += 2) {
        if (num % i == 0) return false;
    }
    return true;
}

int generate_prime() {
    while (true) {
        int num = random(10, 50);
        if (is_prime(num)) {
            return num;
        }
    }
}

void generate_keys(int p, int q, PublicKey &pubKey, PrivateKey &privKey) {
    int n = p * q;
    int phi = (p - 1) * (q - 1);
    
    int e = 3;
    while (e < phi) {
        if (gcd(e, phi) == 1)
            break;
        e += 2;
    }
    
    int d = mod_inverse(e, phi);
    
    pubKey.e = e;
    pubKey.n = n;
    privKey.d = d;
    privKey.n = n;
}

void encrypt_message(const char *message, const PublicKey &pubKey, char *encrypted_message) {
    String buffer = "";
    for (int i = 0; i < strlen(message); i++) {
        long long encrypted_char = mod_exp((long long)message[i], pubKey.e, pubKey.n);
        buffer += String((unsigned long)encrypted_char) + " ";
    }
    strcpy(encrypted_message, buffer.c_str());
}

long long str_to_ll(const char *str) {
    long long result = 0;
    while (*str >= '0' && *str <= '9') {
        result = result * 10 + (*str - '0');
        str++;
    }
    return result;
}

void decrypt_message(const char *encrypted_message, const PrivateKey &privKey, char *decrypted_message) {
    const char *ptr = encrypted_message;
    int index = 0;
    while (*ptr) {
        long long encrypted_char = str_to_ll(ptr);
        long long decrypted_char = mod_exp(encrypted_char, privKey.d, privKey.n);
        decrypted_message[index++] = (char)decrypted_char;
        while (*ptr && *ptr != ' ') ptr++;
        while (*ptr == ' ') ptr++;
    }
    decrypted_message[index] = '\0';
}

PublicKey pubKey;
PrivateKey privKey;

void setup() {
    Serial.begin(9600);
    randomSeed(analogRead(0));
    Serial.println("RSA Encryption Started");

    int p = generate_prime();
    int q = generate_prime();
    while (p == q) {
        q = generate_prime();
    }
    generate_keys(p, q, pubKey, privKey);

    Serial.println("Enter a message to encrypt and decrypt:");
}

void loop() {
    if (Serial.available() > 0) {
        String message = Serial.readStringUntil('\n');
        message.trim();

        Serial.print("Public key: e = ");
        Serial.print(pubKey.e);
        Serial.print(", n = ");
        Serial.println(pubKey.n);

        Serial.print("Private key: d = ");
        Serial.print(privKey.d);
        Serial.print(", n = ");
        Serial.println(privKey.n);

        if (message.length() > 0) {
            Serial.print("Original: ");
            Serial.println(message);

            char encrypted_message[512];
            encrypt_message(message.c_str(), pubKey, encrypted_message);
            Serial.print("Encrypted: ");
            Serial.println(encrypted_message);

            char decrypted_message[512];
            decrypt_message(encrypted_message, privKey, decrypted_message);
            Serial.print("Decrypted: ");
            Serial.println(decrypted_message);
        }
    }
}
