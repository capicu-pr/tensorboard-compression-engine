from setuptools import setup, find_packages

setup(
    name="compression-board-plugin",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[
        "tensorboard>=2.0",
    ],
    entry_points={
        "tensorboard_plugins": [
            # Expose the plugin to TensorBoard as 'compression'.
            "compression = compression_board_plugin.compression_plugin:CompressionPlugin",
        ],
    },
)

