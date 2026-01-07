# Congestion Control Deep-Dive

SyncroX implements industry-standard congestion control algorithms to ensure fair and efficient bandwidth usage, especially over lossy or congested links.

---

## 📉 The Control Variables

*   **`cwnd` (Congestion Window)**: Limits the number of unacknowledged packets in flight.
*   **`ssthresh` (Slow Start Threshold)**: The boundary between "aggressive" growth and "cautious" growth.
*   **`dup_acks`**: Counter for duplicate acknowledgments, used to detect loss without waiting for a timeout.

---

## ⚡ Tahoe Algorithm Logic

Tahoe is a conservative algorithm that treats any sign of loss as a severe congestion event.

### Phase 1: Slow Start (`cwnd < ssthresh`)
*   For every new ACK received: `cwnd = cwnd + 1.0`
*   Effect: `cwnd` doubles every Round Trip Time (RTT).

### Phase 2: Congestion Avoidance (`cwnd >= ssthresh`)
*   For every new ACK received: `cwnd = cwnd + (1.0 / cwnd)`
*   Effect: `cwnd` increases linearly by 1.0 packet per RTT.

### Phase 3: Packet Loss (3 Dup ACKs or Timeout)
*   `ssthresh = max(cwnd / 2, 2.0)`
*   `cwnd = 1.0`
*   Result: Restart from Slow Start.

---

## 🏎️ Reno Algorithm Logic

Reno improves on Tahoe by adding **Fast Recovery**, preventing the throughput from dropping to near-zero during minor packet losses.

### Fast Retransmit & Recovery (On 3 Duplicate ACKs)
1.  **Retransmit**: Immediately re-send the missing packet.
2.  **Adjust Threshold**: `ssthresh = max(cwnd / 2, 2.0)`
3.  **Inflate Window**: `cwnd = ssthresh + 3` (accounting for the 3 packets that already reached the receiver and triggered the dup ACKs).
4.  **Recovery**: For every *additional* duplicate ACK, `cwnd = cwnd + 1`. This allows the sender to keep pushing new data while waiting for the retransmitted packet to be ACKed.
5.  **Exit**: When a *new* ACK arrives (covering the missing packet), set `cwnd = ssthresh` and enter Congestion Avoidance.

---

## 📊 Comparison Table

| Event | Tahoe Action | Reno Action |
| :--- | :--- | :--- |
| **New ACK (Slow Start)** | `cwnd++` | `cwnd++` |
| **New ACK (Avoidance)** | `cwnd += 1/cwnd` | `cwnd += 1/cwnd` |
| **3 Duplicate ACKs** | Reset `cwnd=1`, Slow Start. | Fast Retransmit, **Fast Recovery**. |
| **Timeout** | Reset `cwnd=1`, Slow Start. | Reset `cwnd=1`, Slow Start. |
