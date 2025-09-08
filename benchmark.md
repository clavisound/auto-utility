# Benchmarks

## pdf reading
```
time python3 eyath-reader.py eyath/38-17-077-50-90_ΑΚΝ32848900.pdf 
Processing PDF from file: eyath/38-17-077-50-90_ΑΚΝ32848900.pdf
{
    "RFpayment": "RF08906109000012800574097",
    "startMeasurement": "11/04/2025",
    "endMeasurement": "10/08/2025",
    "duePayment": "27/10/2025",
    "amount": 32.63,
    "consumerNumber": "38-17-077-50-90"
}

real    0m1,262s
user    0m1,196s
sys     0m0,061s
```

# Body reading and auto-deciding.
```
~/git/auto-utility$ time python3 body-reader.py eyath/raw.eml 
{
    "type": "water",
    "company": "eyath",
    "consumerNumber": "38-17-077-50-90",
    "accountNumber": "ΑΚΝ32848900",
    "RFcode": "RF08906109000012800574097",
    "amount": "32.63",
    "paymentDue": "27/10/2025"
}

real    0m0,404s
user    0m0,348s
sys     0m0,051s
```
