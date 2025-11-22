from datasets import load_dataset, DatasetDict
from pydantic import BaseModel
from typing import Callable, Optional, Dict, List, Any


class ConversationalFormatter(BaseModel):
    """Abstraction for loading datasets and formatting them as role/content messages."""
    
    dataset_name: str
    dataset_config: Optional[str] = None
    dataset_kwargs: Optional[Dict[str, Any]] = None
    split: Optional[str] = None
    
    def _load_dataset(self):
        """Load dataset with flexible configuration."""
        kwargs = self.dataset_kwargs or {}
        
        if self.dataset_config:
            return load_dataset(self.dataset_name, self.dataset_config, **kwargs)
        else:
            return load_dataset(self.dataset_name, **kwargs)
    
    def _format_to_messages(
        self, 
        example: Dict[str, Any],
        column_mapping: Optional[Dict[str, str]] = None,
        custom_formatter: Optional[Callable[[Dict[str, Any]], List[Dict[str, str]]]] = None,
        unfold_lists_sequence: list[Any] | None = None
    ) -> List[Dict[str, str]]:
        """
        Format example to role/content messages.
        
        Args:
            example: Dataset example row
            column_mapping: Dict mapping column names to roles, e.g. {"prompt": "user", "response": "assistant"}
            custom_formatter: Custom function that takes example and returns list of {"role": ..., "content": ...}
        
        Returns:
            List of message dicts with "role" and "content" keys
        """
        if custom_formatter:
            return custom_formatter(example)
        
        if column_mapping:
            messages = []
            for column, role in column_mapping.items():
                if column in example:
                    content = example[column]
                    # Handle both single values and lists
                    if isinstance(content, list) and unfold_lists_sequence:
                        for i, item in enumerate(content):
                            messages.append({"role": role, "content": f"{unfold_lists_sequence[i]}. {str(item)}"})
                    else:
                        messages.append({"role": role, "content": str(content)})
            return messages
        
        # Default: assume single "text" column as user message
        if "text" in example:
            content = example["text"]
            if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                # Already in role/content format
                return content
            return [{"role": "user", "content": str(content)}]
        
        raise ValueError("No column_mapping or custom_formatter provided, and no 'text' column found")
    
    def format_dataset(
        self,
        column_mapping: Optional[Dict[str, str]] = None,
        custom_formatter: Optional[Callable[[Dict[str, Any]], List[Dict[str, str]]]] = None,
        output_column: str = "messages"
    ):
        """
        Load dataset and format all examples as role/content messages.
        
        Args:
            column_mapping: Dict mapping column names to roles
            custom_formatter: Custom formatting function
            output_column: Name of output column containing messages
        
        Returns:
            Dataset with messages in role/content format
        """
        dataset = self._load_dataset()
        
        # Handle DatasetDict vs Dataset
        if hasattr(dataset, 'keys'):
            # DatasetDict - process each split
            formatted = {}
            for split_name, split_data in dataset.items():
                formatted[split_name] = self._format_split(
                    split_data, column_mapping, custom_formatter, output_column
                )
            return DatasetDict(formatted)
        else:
            # Single Dataset
            return self._format_split(dataset, column_mapping, custom_formatter, output_column)
    
    def _format_split(
        self,
        dataset,
        column_mapping: Optional[Dict[str, str]],
        custom_formatter: Optional[Callable],
        output_column: str
    ):
        """Format a single dataset split."""
        def format_example(example):
            messages = self._format_to_messages(example, column_mapping, custom_formatter)
            return {output_column: messages}
        
        return dataset.map(format_example, batched=False)



## Multi-turn: multiple columns
#formatter = ConversationalFormatter(dataset_name="cais/wmdp", dataset_config="wmdp-bio")
#dataset = formatter.format_dataset(column_mapping={"question": "user", "answer": "assistant"})
#
## Custom formatting
#def custom_format(example):
#    return [{"role": "user", "content": f"Q: {example['q']}"}, 
#            {"role": "assistant", "content": example['a']}]
#dataset = formatter.format_dataset(custom_formatter=custom_format)
#dataset = formatter.format_dataset(custom_formatter=custom_format)