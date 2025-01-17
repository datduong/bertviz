import torch
from collections import defaultdict


def get_attention(model, tokenizer, text, include_queries_and_keys=False):

  """Compute representation of the attention to pass to the d3 visualization

  Args:
    model: pytorch_transformers model
    tokenizer: pytorch_transformers tokenizer
    text: Input text
    include_queries_and_keys: Indicates whether to include queries/keys in results

  Returns:
    Dictionary of attn representations with the structure:
    {
    'left_text': list of source tokens, to be displayed on the left of the vis
    'right_text': list of target tokens, to be displayed on the right of the vis
    'attn': list of attention matrices, one for each layer. Each has shape (num_heads, source_seq_len, target_seq_len)
    'queries' (optional): list of query vector arrays, one for each layer. Each has shape (num_heads, source_seq_len, vector_size)
    'keys' (optional): list of key vector arrays, one for each layer. Each has shape (num_heads, target_seq_len, vector_size)
    }
  """

  # Prepare inputs to model
  token_ids = tokenizer.encode(text)
  tokens = [tokenizer.decode([t]).strip() for t in token_ids]
  tokens_tensor = torch.tensor(token_ids).unsqueeze(0)

  # Call model to get attention data
  model.eval()
  _, _, attn_data_list = model(tokens_tensor)

  # Format attention data for visualization
  all_attns = []
  all_queries = []
  all_keys = []
  for layer, attn_data in enumerate(attn_data_list):
    attn = attn_data['attn'][0]  # assume batch_size=1; output shape = (num_heads, seq_len, seq_len)
    all_attns.append(attn.tolist())
    if include_queries_and_keys:
      queries = attn_data['queries'][0]  # assume batch_size=1; output shape = (num_heads, seq_len, vector_size)
      all_queries.append(queries.tolist())
      keys = attn_data['keys'][0]  # assume batch_size=1; output shape = (num_heads, seq_len, vector_size)
      all_keys.append(keys.tolist())
  results = {
    'attn': all_attns,
    'left_text': tokens,
    'right_text': tokens
  }
  if include_queries_and_keys:
    results.update({
      'queries': all_queries,
      'keys': all_keys,
    })
  return {'all': results}

def format_sentence_a (sentence_a,tokenizer,shift_counter=0,add_cls=True): 

  sent_a = sentence_a.split('[SEP]')
  sent_a = [tokenizer.tokenize(a.strip()) for a in sent_a] ## tokenize each segment
  if add_cls:
    sent_a[0] = ['[CLS]'] + sent_a[0] ## ADD CLS TO FIRST SEGMENT

  token_type_ids = []
  tokens_a = []
  for counter,t in enumerate(sent_a):
    if len(t) > 0: ## trailing blank ?? 
      tokens_a = tokens_a + t + ['[SEP]'] ## add each token id WITH SEP
      token_type_ids = token_type_ids + len(t + ['[SEP]']) * [counter+shift_counter] ## @shift_counter is needed if we have 2nd sentence with many [sep] as well

  token_ids = tokenizer.convert_tokens_to_ids (tokens_a)

  return tokens_a, token_ids, token_type_ids


def format_sentence_b (sentence_b,tokenizer,index_number=5): 

  tokens_b = tokenizer.tokenize(sentence_b) + ['[SEP]'] ## expect a topic, so we produce ['soccer' 'sep']
  token_ids = tokenizer.convert_tokens_to_ids(tokens_b)
  token_type_ids = [index_number] * len(token_ids)

  return tokens_b, token_ids, token_type_ids



def get_attention_bert(model, tokenizer, sentence_a, sentence_b, include_queries_and_keys=False):

  """Compute representation of the attention for BERT to pass to the d3 visualization

  Args:
    model: BERT model
    tokenizer: BERT tokenizer
    sentence_a: Sentence A string
    sentence_b: Sentence B string
    include_queries_and_keys: Indicates whether to include queries/keys in results

  Returns:
    Dictionary of attn representations with the structure:
    {
    'all': All attention (source = AB, target = AB)
    'aa': Sentence A self-attention (source = A, target = A)
    'bb': Sentence B self-attention (source = B, target = B)
    'ab': Sentence A -> Sentence B attention (source = A, target = B)
    'ba': Sentence B -> Sentence A attention (source = B, target = A)
    }
    where each value is a dictionary:
    {
    'left_text': list of source tokens, to be displayed on the left of the vis
    'right_text': list of target tokens, to be displayed on the right of the vis
    'attn': list of attention matrices, one for each layer. Each has shape [num_heads, source_seq_len, target_seq_len]
    'queries' (optional): list of query vector arrays, one for each layer. Each has shape (num_heads, source_seq_len, vector_size)
    'keys' (optional): list of key vector arrays, one for each layer. Each has shape (num_heads, target_seq_len, vector_size)
    }
  """

  # Prepare inputs to model
  # tokens_a = ['[CLS]'] + tokenizer.tokenize(sentence_a)  + ['[SEP]']
  # tokens_b = tokenizer.tokenize(sentence_b) + ['[SEP]']
  # token_ids = tokenizer.convert_tokens_to_ids(tokens_a + tokens_b)
  # tokens_tensor = torch.tensor([token_ids])
  # token_type_tensor = torch.LongTensor([[0] * len(tokens_a) + [1] * len(tokens_b)])

  tokens_a, token_ids_a, token_type_ids_a = format_sentence_a (sentence_a,tokenizer)
  tokens_b, token_ids_b, token_type_ids_b = format_sentence_a (sentence_b,tokenizer,shift_counter=4,add_cls=False)
  # tokens_b, token_ids_b, token_type_ids_b = format_sentence_b (sentence_b,tokenizer)
  
  tokens_tensor = torch.tensor( [token_ids_a + token_ids_b] )
  token_type_tensor = torch.LongTensor( [token_type_ids_a + token_type_ids_b] )

  print ('see word token indexing, and tensor type indexing')
  print (tokens_tensor)
  print (token_type_tensor)

  # Call model to get attention data
  model.eval()
  output = model(tokens_tensor, token_type_ids=token_type_tensor)
  attn_data_list = output[-1]

  ## how exactly do we want to output the results? user_data + tweet_text --> topic ?? 

  # Populate map with attn data and, optionally, query, key data
  keys_dict = defaultdict(list)
  queries_dict = defaultdict(list)
  attn_dict = defaultdict(list)

  ## must fix the slicing here. ?? well, depend how we want to split the sentence
  slice_a = slice(0, len(tokens_a))  # Positions corresponding to sentence A in input
  slice_b = slice(len(tokens_a), len(tokens_a) + len(tokens_b))  # Position corresponding to sentence B in input

  ## want user_data tweet_text (token type=5) then tweet_topic (token type=6) ### need some shifting ???

  for layer, attn_data in enumerate(attn_data_list):
    # Process attention
    attn = attn_data['attn'][0]  # assume batch_size=1; shape = [num_heads, source_seq_len, target_seq_len]
    attn_dict['all'].append(attn.tolist())
    print ('layer {}'.format(layer))
    print (attn[:, slice_a, slice_a])
    attn_dict['aa'].append(attn[:, slice_a, slice_a].tolist())  # Append A->A attention for layer, across all heads
    attn_dict['bb'].append(attn[:, slice_b, slice_b].tolist())  # Append B->B attention for layer, across all heads
    attn_dict['ab'].append(attn[:, slice_a, slice_b].tolist())  # Append A->B attention for layer, across all heads
    attn_dict['ba'].append(attn[:, slice_b, slice_a].tolist())  # Append B->A attention for layer, across all heads
    # Process queries and keys
    if include_queries_and_keys:
      queries = attn_data['queries'][0]  # assume batch_size=1; shape = [num_heads, seq_len, vector_size]
      keys = attn_data['keys'][0]  # assume batch_size=1; shape = [num_heads, seq_len, vector_size]
      queries_dict['all'].append(queries.tolist())
      keys_dict['all'].append(keys.tolist())
      queries_dict['a'].append(queries[:, slice_a, :].tolist())
      keys_dict['a'].append(keys[:, slice_a, :].tolist())
      queries_dict['b'].append(queries[:, slice_b, :].tolist())
      keys_dict['b'].append(keys[:, slice_b, :].tolist())

  results = {
    'all': {
      'attn': attn_dict['all'],
      'left_text': tokens_a + tokens_b,
      'right_text': tokens_a + tokens_b
    },
    'aa': {
      'attn': attn_dict['aa'],
      'left_text': tokens_a,
      'right_text': tokens_a
    },
    'bb': {
      'attn': attn_dict['bb'],
      'left_text': tokens_b,
      'right_text': tokens_b
    },
    'ab': {
      'attn': attn_dict['ab'],
      'left_text': tokens_a,
      'right_text': tokens_b
    },
    'ba': {
      'attn': attn_dict['ba'],
      'left_text': tokens_b,
      'right_text': tokens_a
    }
  }
  if include_queries_and_keys:
    results['all'].update({
      'queries': queries_dict['all'],
      'keys': keys_dict['all'],
    })
    results['aa'].update({
      'queries': queries_dict['a'],
      'keys': keys_dict['a'],
    })
    results['bb'].update({
      'queries': queries_dict['b'],
      'keys': keys_dict['b'],
    })
    results['ab'].update({
      'queries': queries_dict['a'],
      'keys': keys_dict['b'],
    })
    results['ba'].update({
      'queries': queries_dict['b'],
      'keys': keys_dict['a'],
    })
  return results


