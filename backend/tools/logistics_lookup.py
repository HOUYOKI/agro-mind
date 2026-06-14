import os
import json

def lookup_order(user_query: str, customer_id: str = None) -> dict:
    """
    Looks up shipping and logistics data from the JSON Lines database.
    """
    fallback_response = {
        "order_found": False,
        "order_id": None,
        "status": None,
        "eta": None,
        "tracking_number": None,
        "reason": "Order or customer details not found in the logistics database."
    }
    
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__)) 
        backend_dir = os.path.dirname(current_dir)              
        data_file_path = os.path.join(backend_dir, "data", "orders.jsonl")
        
        if not os.path.exists(data_file_path):
            return {
                **fallback_response,
                "reason": f"Database file not found at: {data_file_path}"
            }

        with open(data_file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                order_data = json.loads(line)
                
                if str(order_data.get("customer_id")) == str(customer_id):
                    return {
                        "order_found": True,
                        "order_id": order_data.get("order_id"),
                        "status": order_data.get("status"),
                        "eta": order_data.get("eta"),
                        "tracking_number": order_data.get("tracking_number"),
                        "reason": f"The item '{order_data.get('product')}' is currently [{order_data.get('status')}] at {order_data.get('current_location')}."
                    }
                    
        return fallback_response

    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}") 
        return {
            "order_found": False,
            "order_id": None,
            "status": None,
            "eta": None,
            "tracking_number": None,
            "reason": f"System error occurred. Technical details: {str(e)}"
         
         }
         
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}") 
        return {
            "order_found": False,
            "order_id": None,
            "status": None,
            "eta": None,
            "tracking_number": None,
            "reason": f"System error occurred. Technical details: {str(e)}"
        }