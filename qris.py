def calculate_crc16(payload: str) -> str:
    crc = 0xFFFF
    for char in payload:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"

def generate_dynamic_qris(base_qris: str, amount: int) -> str:
    """
    Takes a static QRIS string and injects the transaction amount (tag 54).
    """
    # Remove the existing CRC (tag 63 length 04 + 4 bytes CRC) -> last 8 chars
    if base_qris.startswith("000201"):
        # Just to be safe, find the "6304" tag at the end
        if "6304" in base_qris[-8:]:
            base_qris = base_qris[:-4] # remove the 4 byte CRC
        else:
            # If not formatted exactly as expected at the end, find 6304
            idx = base_qris.rfind("6304")
            if idx != -1:
                base_qris = base_qris[:idx+4]
            else:
                base_qris += "6304"
                
    amount_str = str(amount)
    amount_len = f"{len(amount_str):02d}"
    tag_54 = f"54{amount_len}{amount_str}"
    
    # We should insert tag 54 before tag 58.
    # Usually QRIS ends with 5802ID59... 6304
    # Let's find 5802ID and insert before it
    idx_58 = base_qris.find("5802ID")
    if idx_58 != -1:
        new_qris = base_qris[:idx_58] + tag_54 + base_qris[idx_58:]
    else:
        # Just append before 6304
        idx_63 = new_qris.rfind("6304")
        new_qris = base_qris[:idx_63] + tag_54 + base_qris[idx_63:]
        
    # Calculate CRC
    crc = calculate_crc16(new_qris)
    return new_qris + crc

if __name__ == "__main__":
    # Test
    default = "00020101021126610014COM.GO-JEK.WWW01189360091439188482260210G9188482260303UMI51440014ID.CO.QRIS.WWW0215ID10264831152460303UMI5204581253033605802ID5924Hehe foodstore, PGDANGAN6009TANGERANG61051533462070703A016304BF71"
    dyn = generate_dynamic_qris(default, 15000)
    print("Static:", default)
    print("Dynamic:", dyn)
