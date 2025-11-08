# CodePulse_AI
Hackathon Project


Commands:

- Open new terminal and go to backend Folder and run:
python -m venv venv (only once)
.\venv\Scripts\activate.bat

- Open new terminal and go to frontend Folder and run:
npm install (only once)
npm start

- Open new terminal and come to root folder and run:
docker-compose up -d backend
docker-compose logs -f backend

To check if all services are up:
python tests/test_scenarios.py

To view ne04j data on UI:
http://localhost:7474 (verify graph data)


# Test Neo4j
open http://localhost:7474
# Query: MATCH (n) RETURN n LIMIT 10

# 4. Test Backend
curl http://localhost:8000/health
# Should return: {"status":"ok"}

# 5. Test Frontend
open http://localhost:3000
# Should see: CodeFlow Catalyst dashboard

# 6. Run pre-flight check
python tests/test_scenarios.py
# Should show: All systems ready


- Loading hardcoded data via curl commands:
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "sample-repo/banking-app/src/payment/PaymentProcessor.java",
    "repository": "banking-app",
    "diff": "- return amount * 0.03;\n+ return amount * 0.025 + 15.0;"
  }'


curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "sample-repo/banking-app/src/payment/PaymentProcessor.java",
    "repository": "banking-app-disaster",
    "diff": "@@ -30,15 +30,25 @@ public class PaymentProcessor {\n     \n     public PaymentResult processPayment(Payment payment) {\n-        // Step 1: Validate payment\n-        if (!validatePayment(payment)) {\n-            return PaymentResult.failed(\"Invalid payment data\");\n-        }\n+        // CRITICAL CHANGE: Removed validation step - SECURITY RISK\n         \n-        // Step 2: Check account balance\n-        double currentBalance = accountBalance.getBalance(payment.getAccountId());\n-        if (currentBalance < payment.getAmount()) {\n-            return PaymentResult.failed(\"Insufficient funds\");\n-        }\n+        // BREAKING: Changed balance check logic\n+        // Now allows negative balances (overdraft feature)\n+        double currentBalance = accountBalance.getBalance(payment.getAccountId());\n+        double overdraftLimit = getOverdraftLimit(payment.getAccountId());\n+        \n+        if (currentBalance + overdraftLimit < payment.getAmount()) {\n+            // CRITICAL: Still process with manual review flag\n+            payment.setRequiresManualReview(true);\n+        }\n         \n-        // Step 3: Fraud detection\n-        boolean isFraudulent = fraudDetection.checkTransaction(payment);\n-        if (isFraudulent) {\n-            return PaymentResult.rejected(\"Fraud detected\");\n-        }\n+        // BREAKING CHANGE: FraudDetection method signature changed\n+        TransactionContext context = new TransactionContext(\n+            payment.getDeviceId(),\n+            payment.getIpAddress(),\n+            payment.getGeoLocation()\n+        );\n+        \n+        FraudResult fraudResult = fraudDetection.checkTransaction(payment, context);\n+        if (fraudResult.isFraudulent() && fraudResult.getRiskScore() > 0.95) {\n+            // CHANGED: Only block super high-risk (was blocking all fraud)\n+            return PaymentResult.rejected(\"High-risk fraud detected\");\n+        }\n         \n         // Step 4: Calculate fee\n-        double fee = calculateFee(payment.getAmount(), payment.getType());\n-        payment.setFee(fee);\n+        // CRITICAL: Fee calculation now includes dynamic pricing\n+        double baseFee = calculateFee(payment.getAmount(), payment.getType());\n+        double surgeMultiplier = getSurgeMultiplier(); // Peak hour pricing\n+        double finalFee = baseFee * surgeMultiplier;\n+        payment.setFee(finalFee);\n+        \n+        // CRITICAL: New database schema - added columns\n+        payment.setProcessedAt(System.currentTimeMillis());\n+        payment.setFraudScore(fraudResult.getRiskScore());\n+        payment.setOverdraftUsed(currentBalance < 0);\n         \n         // Step 5: Process payment\n-        transactionDAO.save(payment);\n+        // BREAKING: Changed to async processing\n+        CompletableFuture.runAsync(() -> {\n+            transactionDAO.save(payment);\n+            // NEW: Publish to event bus\n+            eventBus.publish(\"payment.processed\", payment);\n+        });\n         \n-        // Step 6: Update balance\n-        accountBalance.updateBalance(\n-            payment.getAccountId(), \n-            payment.getAmount() + fee\n-        );\n+        // CRITICAL: Balance update now includes overdraft\n+        double totalDebit = payment.getAmount() + finalFee;\n+        accountBalance.updateBalanceWithOverdraft(\n+            payment.getAccountId(),\n+            totalDebit,\n+            overdraftLimit\n+        );\n         \n         // Step 7: Send notification\n-        sendNotification(payment);\n+        // NEW: Multi-channel notifications\n+        NotificationPreference pref = getNotificationPreference(payment.getAccountId());\n+        if (pref.isEmailEnabled()) sendEmail(payment);\n+        if (pref.isSmsEnabled()) sendSMS(payment);\n+        if (pref.isPushEnabled()) sendPushNotification(payment);\n+        if (payment.getAmount() > 10000) notifyComplianceTeam(payment);\n         \n         return PaymentResult.success(payment.getId());\n     }\n+    \n+    private double getOverdraftLimit(String accountId) {\n+        // NEW: Fetch overdraft limit from database\n+        return customerDAO.getOverdraftLimit(accountId);\n+    }\n+    \n+    private double getSurgeMultiplier() {\n+        // NEW: Dynamic pricing based on system load\n+        int currentLoad = systemMetrics.getCurrentLoad();\n+        if (currentLoad > 80) return 1.5;\n+        if (currentLoad > 60) return 1.2;\n+        return 1.0;\n+    }"
  }'


- Loading data via running file: 
python scripts/load_demo_data.py
