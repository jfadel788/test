from urllib.parse import urlparse
from flask import Flask, request, jsonify
from scraper.scraper_service import *
import json
from scraper.scraper_schema import InputSchema
from marshmallow import Schema, fields, ValidationError




def check_validity():
    try:
        
        input_schema = InputSchema()
        data = input_schema.load(request.get_json())

    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400


    url = data['url']
    description = data['description']
    price = data['price']

   
    result = fetch_product(url)
    if "error" in result:
        return jsonify({"error": result["error"]}), 500

    scraped_price = result.get('price')
    if not scraped_price:
        return jsonify({"error": "Scraped price not found"}), 500

  
    print(f"Raw scraped_price: {scraped_price}, type: {type(scraped_price)}")

   
    if isinstance(scraped_price, str):
        try:
            extracted_price = extract_numerical_price(scraped_price) 
        except ValueError as e:
            return jsonify({"error": f"Price extraction failed: {str(e)}"}), 500
        
    elif isinstance(scraped_price, (int, float)):
        extracted_price = float(scraped_price)
        
    else:
        return jsonify({"error": f"Unexpected price format: {scraped_price} of type {type(scraped_price)}"}), 500

   
    print(f"Extracted numeric price: {extracted_price}, type: {type(extracted_price)}")

    score = calculate_match_score(price, extracted_price)
    prompt = generate_prompt(price, extracted_price, score)

    
    try:
        comparison_result = get_completion(prompt)

       
        if not comparison_result:
            return jsonify({"error": "No response received from Claude model."}), 500

        
        if isinstance(comparison_result, list) and 'text' in comparison_result[0]:
            result_text = comparison_result[0]['text']
        else:
            return jsonify({"error": "Unexpected response format from Claude model."}), 500

        
        start_index = result_text.find("{")
        end_index = result_text.rfind("}") + 1

        if start_index != -1 and end_index != -1:
            
            json_string = result_text[start_index:end_index]
            parsed_json = json.loads(json_string)

            formatted_result = {
                "score": parsed_json.get("match_score"),
                "analysis": parsed_json.get("analysis")
            }
            return jsonify({"result": formatted_result})
        else:
            return jsonify({"error": "Failed to extract JSON from the response."}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    